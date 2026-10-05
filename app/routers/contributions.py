from app.services.badges import award_badges
from datetime import datetime
import shutil
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.models.contribution import Contribution, ContributionAudit, XPTransaction
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.notification import Notification
from app.services import contributions as storage

router=APIRouter(prefix='/admin/contributions',tags=['Contribution moderation'],dependencies=[Depends(require_role('librarian','admin'))])

class Decision(BaseModel):
    decision: Literal['APPROVED','REJECTED']
    reason: str|None=Field(None,max_length=2000)
    @model_validator(mode='after')
    def rejection_reason(self):
        self.reason=self.reason.strip() if self.reason else None
        if self.decision=='REJECTED' and not self.reason:raise ValueError('A rejection reason is required')
        return self

@router.get('')
def queue(status: Literal['PENDING','APPROVED','REJECTED']='PENDING', page: int=Query(1,ge=1), kind: Literal['note','question_paper','question_bank','study_material']|None=None, search: str=Query('',max_length=200), db: Session=Depends(get_db)):
    query=db.query(Contribution).filter(Contribution.status==status)
    if kind:query=query.filter(Contribution.kind==kind)
    if search.strip():
        term='%'+search.strip()+'%'
        query=query.join(User,User.id==Contribution.user_id).filter(Contribution.title.ilike(term)|Contribution.subject.ilike(term)|User.name.ilike(term))
    rows=query.order_by(Contribution.created_at,Contribution.id).offset((page-1)*20).limit(20).all()
    names=dict(db.query(User.id,User.name).filter(User.id.in_([r.user_id for r in rows])).all()) if rows else {}
    return {'total':query.count(),'items':[{'id':r.id,'title':r.title,'kind':r.kind,'subject':r.subject,
        'student':names.get(r.user_id,'Unknown'),'course_code':r.course_code,'semester':r.semester,'branch':r.branch,
        'exam_type':r.exam_type,'academic_year':r.academic_year,'college':r.college,'filename':r.original_name,
        'status':r.status,'created_at':r.created_at,'reviewed_at':r.reviewed_at,'rejection_reason':r.rejection_reason} for r in rows]}

@router.get('/{id}/file')
def preview(id: int,db: Session=Depends(get_db)):
    row=db.get(Contribution,id)
    if not row:raise HTTPException(404,'Contribution not found')
    path=storage.private_path(row.storage_name)
    if not path.is_file():raise HTTPException(404,'Contribution file not found')
    return FileResponse(path,media_type='application/pdf' if path.suffix=='.pdf' else 'text/plain',
                        filename=row.original_name,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

@router.post('/{id}/decision')
def decide(id: int,payload: Decision,db: Session=Depends(get_db),staff: User=Depends(require_role('librarian','admin'))):
    row=db.query(Contribution).filter(Contribution.id==id).with_for_update().first()
    if not row:raise HTTPException(404,'Contribution not found')
    if row.user_id==staff.id:raise HTTPException(403,'You cannot review your own contribution')
    if row.status==payload.decision:return {'status':row.status,'id':row.id}
    if row.status!='PENDING':raise HTTPException(409,'This contribution has already been reviewed')
    published=None
    try:
        if payload.decision=='APPROVED':
            source=storage.private_path(row.storage_name)
            if not source.is_file():raise HTTPException(409,'File is missing; approval cannot proceed')
            storage.PUBLIC_DIR.mkdir(parents=True,exist_ok=True)
            published=storage.PUBLIC_DIR/row.storage_name
            shutil.copyfile(source,published)
            common=dict(title=row.title,subject=row.subject,semester=row.semester,user_id=row.user_id,
                        file_url='/uploads/contributions/'+row.storage_name,file_type=source.suffix[1:].upper())
            if row.kind in ('question_paper','question_bank'):
                if not row.semester or not row.branch:raise HTTPException(422,'Question resources require semester and branch before approval')
                item=QuestionBank(**common,branch=row.branch,exam_type=row.exam_type or 'Practice Set',academic_year=row.academic_year or '',total_questions=0)
                db.add(item);db.flush();row.question_bank_id=item.id
            else:
                item=Note(**common,branch=row.branch,status='published',access_level='public',file_size=f'{source.stat().st_size} bytes')
                db.add(item);db.flush();row.note_id=item.id
            db.add(XPTransaction(user_id=row.user_id,event_key=f'contribution:{row.id}:approved',amount=2))
        row.status=payload.decision;row.reviewer_id=staff.id;row.reviewed_at=datetime.utcnow()
        row.rejection_reason=payload.reason if payload.decision=='REJECTED' else None
        db.add(ContributionAudit(contribution_id=row.id,staff_id=staff.id,decision=payload.decision,reason=payload.reason))
        db.add(Notification(user_id=row.user_id,message=f'Your contribution "{row.title}" was {payload.decision.lower()}.'+((' Reason: '+payload.reason) if payload.decision=='REJECTED' and payload.reason else ''),is_read=False))
        db.flush()
        from app.services.badges import award_badges
        award_badges(db, row.user_id)
        db.commit()
    except Exception:
        db.rollback()
        if published:published.unlink(missing_ok=True)
        raise
    return {'status':row.status,'id':row.id}
