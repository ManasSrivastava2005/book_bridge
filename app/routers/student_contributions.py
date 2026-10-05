import hashlib,json
from pathlib import Path
from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,UploadFile,File,Form,HTTPException,Query
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel,Field,ConfigDict,ValidationError,model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.models.contribution import Contribution
from app.services import contributions as storage
router=APIRouter(prefix='/student/contributions',tags=['Student contributions'])
class Submission(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    title:str=Field(min_length=1,max_length=255)
    subject:str=Field(min_length=1,max_length=100)
    kind:Literal['note','question_paper','question_bank','study_material']
    course_code:str|None=Field(None,max_length=50)
    semester:int|None=Field(None,ge=1,le=20)
    branch:str|None=Field(None,max_length=100)
    exam_type:str|None=Field(None,max_length=50)
    academic_year:str|None=Field(None,max_length=20)
    college:str|None=Field(None,max_length=200)
    @model_validator(mode='after')
    def question_metadata(self):
        if self.kind in ('question_paper','question_bank') and (not self.semester or not self.branch):raise ValueError('Question resources require semester and branch')
        return self

def output(row):
    return {'id':row.id,'title':row.title,'subject':row.subject,'kind':row.kind,'status':row.status,'rejection_reason':row.rejection_reason,'created_at':row.created_at,'reviewed_at':row.reviewed_at,'filename':row.original_name}

@router.post('',status_code=201)
async def submit(metadata:str=Form(...),request_key:UUID=Form(...),file:UploadFile=File(...),db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    try:payload=Submission.model_validate_json(metadata)
    except ValidationError:raise HTTPException(422,'Check title, subject, type and academic metadata') from None
    content=await file.read(25*1024*1024+1)
    if not content or len(content)>25*1024*1024:raise HTTPException(422,'Choose a nonempty PDF or text file up to 25 MB')
    filename=Path(file.filename or 'file').name[:180]
    digest=hashlib.sha256(payload.model_dump_json().encode()+filename.encode()+content).hexdigest()
    db.query(User).filter_by(id=user.id).with_for_update().one()
    existing=db.query(Contribution).filter_by(user_id=user.id,request_key=str(request_key)).first()
    if existing:
        if existing.payload_hash!=digest:raise HTTPException(409,'This upload request already contains a different submission')
        return output(existing)
    storage_name=None
    try:
        storage_name=await run_in_threadpool(storage.store_pending_file,filename,content)
        row=Contribution(user_id=user.id,storage_name=storage_name,original_name=filename,status='PENDING',request_key=str(request_key),payload_hash=digest,**payload.model_dump())
        db.add(row);db.flush();result=output(row);db.commit();return result
    except Exception:
        db.rollback()
        if storage_name:storage.private_path(storage_name).unlink(missing_ok=True)
        raise

@router.get('')
def listing(page:int=Query(1,ge=1),section:Literal['notes','questions']|None=None,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    query=db.query(Contribution).filter_by(user_id=user.id)
    if section:
        kinds=('note','study_material') if section=='notes' else ('question_paper','question_bank')
        query=query.filter(Contribution.kind.in_(kinds))
    return {'total':query.count(),'page':page,'items':[output(r) for r in query.order_by(Contribution.created_at.desc(),Contribution.id.desc()).offset((page-1)*20).limit(20)]}

@router.get('/{contribution_id}/file')
def file(contribution_id:int,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    row=db.query(Contribution).filter_by(id=contribution_id,user_id=user.id).first()
    if not row:raise HTTPException(404,'Contribution not found')
    path=storage.private_path(row.storage_name)
    if not path.is_file():raise HTTPException(404,'Contribution file not found')
    return FileResponse(path,filename=row.original_name,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
