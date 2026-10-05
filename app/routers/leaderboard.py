from datetime import datetime,timezone,timedelta
from typing import Literal
from fastapi import APIRouter,Depends,Query
from sqlalchemy import func,case,and_
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User,UserRole
from app.models.contribution import XPTransaction
from app.services.xp import level_from_xp
from app.routers.reading_activity import streak_data
router=APIRouter(prefix='/leaderboard',tags=['Leaderboard'])

def now_utc():return datetime.now(timezone.utc).replace(tzinfo=None)

@router.get('')
def leaderboard(period:Literal['weekly','monthly','all_time']='weekly',scope:Literal['all','branch','semester']='all',page:int=Query(1,ge=1),db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    now=now_utc();start=None
    if period=='weekly':start=now.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=now.weekday())
    if period=='monthly':start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    earned=XPTransaction.amount if start is None else case((and_(XPTransaction.created_at>=start,XPTransaction.created_at<=now),XPTransaction.amount),else_=0)
    totals=db.query(XPTransaction.user_id.label('uid'),func.sum(earned).label('xp'),func.sum(XPTransaction.amount).label('lifetime')).group_by(XPTransaction.user_id).subquery()
    xp=func.coalesce(totals.c.xp,0)
    query=db.query(User.id.label('uid'),User.name,User.profile_image, xp.label('xp'),func.coalesce(totals.c.lifetime,0).label('lifetime'),func.row_number().over(order_by=(xp.desc(),User.id.asc())).label('rank')).outerjoin(totals,totals.c.uid==User.id).filter(User.role==UserRole.STUDENT)
    missing=False
    if scope=='branch':
        missing=not bool(user.branch);query=query.filter(User.branch==user.branch) if not missing else query.filter(False)
    if scope=='semester':
        missing=not bool(user.semester);query=query.filter(User.semester==user.semester) if not missing else query.filter(False)
    ranked=query.subquery();rows=db.query(ranked).order_by(ranked.c.rank).offset((page-1)*50).limit(50).all()
    def display(row):
        reading=streak_data(db,row.uid)
        return {'rank':row.rank,'name':row.name,'avatar':row.profile_image,'xp':row.xp,'level':level_from_xp(row.lifetime)['level'],'reading_streak':reading['current_streak'],'pages_read':reading['pages_read'],'is_current':row.uid==user.id}
    own=db.query(ranked).filter(ranked.c.uid==user.id).first()
    return {'items':[display(r) for r in rows],'current_student':display(own) if own else None,'total':db.query(ranked).count(),'page':page,'page_size':50,'period':period,'scope':scope,'calendar_timezone':'UTC','filter_unavailable':missing}
