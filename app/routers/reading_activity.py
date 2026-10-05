"""Server-timed reading with owner locks, one active session and daily unique pages."""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from pypdf import PdfReader
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.reading_activity import ReadingActivity
from app.models.reading_session import ReadingSession, ReadingDay
from app.models.contribution import XPTransaction
from app.routers.reader import check_resource
from app.services import ebook_storage

router = APIRouter(prefix='/reading', tags=['Reading activity'])
def now_utc(): return datetime.now(timezone.utc).replace(tzinfo=None)
def lock_user(db, user):
    return db.query(User).filter(User.id == user.id).with_for_update().one()
def qualified(row): return len(row.pages) >= 10 or row.duration_seconds >= 900

def streak_data(db, user_id, today=None):
    today = today or now_utc().date()
    rows = db.query(ReadingDay).filter(ReadingDay.user_id == user_id).order_by(ReadingDay.date).all()
    dates = [r.date for r in rows if qualified(r)]
    longest = run = 0; previous = None
    for day in dates:
        run = run + 1 if previous and day == previous + timedelta(days=1) else 1
        longest = max(longest, run); previous = day
    current = run if previous and previous in (today, today-timedelta(days=1)) else 0
    return {'current_streak':current, 'longest_streak':longest, 'last_qualifying_date':previous,
            'reading_seconds':sum(r.duration_seconds for r in rows), 'pages_read':sum(len(r.pages) for r in rows)}

@router.get('/summary')
def summary(db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    return streak_data(db, user.id)

@router.post('/sessions/{resource_id}')
def start(resource_id: int, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    lock_user(db,user)
    resource = check_resource(db,resource_id,user)
    if not ebook_storage.managed(resource.file_url):
        raise HTTPException(422,'Reading rewards require a library-uploaded PDF whose pages the server can verify.')
    path=ebook_storage.PRIVATE_EBOOK_DIR/resource.file_url.rsplit('/',1)[-1]
    try:
        with path.open('rb') as file: total=len(PdfReader(file).pages)
    except Exception:
        raise HTTPException(422,'This PDF cannot be verified for reading rewards.') from None
    now=now_utc()
    db.query(ReadingSession).filter(ReadingSession.user_id==user.id,ReadingSession.ended_at.is_(None)).update({'ended_at':now})
    row=ReadingSession(id=str(uuid.uuid4()),user_id=user.id,resource_id=resource_id,started_at=now,last_ping=now,total_pages=total)
    db.add(row);db.commit()
    return {'session_id':row.id,'sequence':0}

class Heartbeat(BaseModel):
    model_config=ConfigDict(extra='forbid')
    sequence: int=Field(ge=1)
    page: int=Field(ge=1)
    active: bool

@router.post('/sessions/{session_id}/heartbeat')
def heartbeat(session_id: str, payload: Heartbeat, db: Session=Depends(get_db), user: User=Depends(get_current_user)):
    lock_user(db,user)
    row=db.query(ReadingSession).filter_by(id=session_id,user_id=user.id).first()
    if not row: raise HTTPException(404,'Reading session not found')
    if row.ended_at: raise HTTPException(409,'Reading session ended; reopen the reader to begin again.')
    check_resource(db,row.resource_id,user)
    if payload.page>row.total_pages: raise HTTPException(422,'Page is outside this document')
    if payload.sequence<=row.sequence:return {'sequence':row.sequence,'duplicate':True}
    if payload.sequence!=row.sequence+1:raise HTTPException(409,'Reading heartbeat sequence is out of order')
    now=now_utc();elapsed=(now-row.last_ping).total_seconds()
    credit=int(elapsed) if 10<=elapsed<=45 and payload.active and now.date()==row.last_ping.date() else 0
    day=db.query(ReadingDay).filter_by(user_id=user.id,date=now.date()).first()
    if not day:
        day=ReadingDay(user_id=user.id,date=now.date(),duration_seconds=0,pages=[]);db.add(day)
    row.page_seconds=(row.page_seconds+credit) if payload.page==row.last_page and credit else 0
    key=f'{row.resource_id}:{payload.page}'
    if row.page_seconds>=30 and key not in day.pages:day.pages=[*day.pages,key]
    row.last_page=payload.page;row.last_ping=now;row.sequence=payload.sequence
    row.duration_seconds+=credit;day.duration_seconds+=credit
    db.flush()
    if qualified(day) and user.role.value=='student':
        for kind in ('READING','STREAK'):
            if kind=='STREAK':
                yesterday=db.query(ReadingDay).filter_by(user_id=user.id,date=day.date-timedelta(days=1)).first()
                if not yesterday or not qualified(yesterday):continue
            key=f'{kind}:{user.id}:{day.date.isoformat()}'
            if not db.query(XPTransaction.id).filter_by(event_key=key).first():
                db.add(XPTransaction(user_id=user.id,amount=25,event_type=kind,event_key=key,description='Meaningful reading' if kind=='READING' else 'Reading streak continuation'))
        activity=db.query(ReadingActivity).filter_by(user_id=user.id).first()
        if not activity:activity=ReadingActivity(user_id=user.id);db.add(activity)
        activity.reading_streak=streak_data(db,user.id,day.date)['current_streak'];activity.last_active_date=now
    from app.services.badges import award_badges
    award_badges(db, user.id)
    db.commit()
    return {'sequence':row.sequence,'qualified':qualified(day),'pages_read':len(day.pages),'duration_seconds':day.duration_seconds}
