from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict,model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.announcement import Announcement,AnnouncementDelivery
from app.models.notification import Notification
from app.models.user import User,UserRole
from app.models.curriculum import Curriculum,CurriculumNode,SubjectEnrollment

router=APIRouter(prefix='/admin/announcements',tags=['Staff announcements'],dependencies=[Depends(require_role('librarian','admin'))])
class AnnouncementWrite(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    title:str=Field(min_length=1,max_length=150)
    message:str=Field(min_length=1,max_length=2000)
    category:Literal['library_notice','due_date','new_resource','reservation','exam','maintenance']='library_notice'
    target_kind:Literal['all','branch','semester','subject','individual']='all'
    target_value:str|None=Field(None,max_length=120)
    @model_validator(mode='after')
    def target(self):
        if self.target_kind!='all' and not self.target_value:raise ValueError('Choose an audience')
        if self.target_kind in ('semester','subject','individual'):
            try:value=int(self.target_value)
            except (ValueError,TypeError):raise ValueError('Audience must be a valid ID or semester')
            if value<=0 or (self.target_kind=='semester' and value>20):raise ValueError('Invalid audience')
        if self.target_kind=='all':self.target_value=None
        return self

def audience(db,row):
    query=db.query(User).filter(User.role==UserRole.STUDENT)
    if row.target_kind=='branch':query=query.filter(User.branch==row.target_value)
    elif row.target_kind=='semester':query=query.filter(User.semester==int(row.target_value))
    elif row.target_kind=='individual':query=query.filter(User.id==int(row.target_value))
    elif row.target_kind=='subject':query=query.join(SubjectEnrollment,SubjectEnrollment.user_id==User.id).filter(SubjectEnrollment.subject_id==int(row.target_value))
    return query

def validate_target(db,row):
    if row.target_kind=='subject':
        subject=db.get(CurriculumNode,int(row.target_value))
        if not subject or subject.kind!='subject' or db.get(Curriculum,subject.curriculum_id).owner_user_id is not None:raise HTTPException(422,'Subject not found')
    if row.target_kind=='individual' and not audience(db,row).first():raise HTTPException(422,'Student not found')

@router.get('/audiences')
def options(db:Session=Depends(get_db)):
    students=db.query(User).filter(User.role==UserRole.STUDENT).order_by(User.name).all()
    subjects=db.query(CurriculumNode,Curriculum).join(Curriculum,Curriculum.id==CurriculumNode.curriculum_id).filter(CurriculumNode.kind=='subject',Curriculum.archived==False,Curriculum.owner_user_id.is_(None)).all()
    return {'branches':sorted({u.branch for u in students if u.branch}),
            'students':[{'id':u.id,'name':u.name,'student_id':u.student_id} for u in students],
            'subjects':[{'id':n.id,'title':f'{n.title} · {c.college} · {c.title} v{c.version}'} for n,c in subjects]}

@router.get('')
def listing(db:Session=Depends(get_db)):
    return db.query(Announcement).order_by(Announcement.id.desc()).limit(100).all()

@router.post('/preview')
def preview(payload:AnnouncementWrite,db:Session=Depends(get_db)):
    validate_target(db,payload);return {'recipients':audience(db,payload).count()}

@router.post('',status_code=201)
def create(payload:AnnouncementWrite,db:Session=Depends(get_db),staff:User=Depends(require_role('librarian','admin'))):
    validate_target(db,payload);row=Announcement(**payload.model_dump(),created_by=staff.id);db.add(row);db.commit();db.refresh(row);return row

@router.post('/{id}/send')
def send(id:int,db:Session=Depends(get_db)):
    row=db.query(Announcement).filter_by(id=id).with_for_update().first()
    if not row:raise HTTPException(404,'Announcement not found')
    if row.sent_at:return {'sent':db.query(AnnouncementDelivery).filter_by(announcement_id=id).count(),'already_sent':True}
    validate_target(db,row);users=audience(db,row).all()
    if not users:raise HTTPException(409,'No students match this audience')
    for user in users:
        notification=Notification(user_id=user.id,message=row.title+'\n'+row.message,is_read=False)
        db.add(notification);db.flush();db.add(AnnouncementDelivery(announcement_id=id,user_id=user.id,notification_id=notification.id))
    row.sent_at=datetime.now(timezone.utc).replace(tzinfo=None);db.commit()
    return {'sent':len(users),'already_sent':False}
