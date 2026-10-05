"""Staff directory: explicit academic/circulation fields, no private documents."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.models.academic_profile import AcademicProfile
from app.models.curriculum import CurriculumNode, SubjectEnrollment
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.schemas.user import UserResponse
from app.schemas.borrow import BorrowResponse
from app.schemas.reservation import ReservationResponse
from app.routers.admin import database_now

router=APIRouter(prefix='/admin/student-data',tags=['Student Data'],dependencies=[Depends(require_role('librarian','admin'))])

class StudentDirectory(BaseModel):
    items:list[UserResponse]
    total:int
    page:int
    page_size:int
    branches:list[str]

class SubjectSummary(BaseModel):
    id:int|None=None
    title:str
    source:str

class AcademicSummary(BaseModel):
    college:str|None=None
    program:str|None=None
    specialization:str|None=None
    subjects:list[SubjectSummary]

class StudentDetail(BaseModel):
    student:UserResponse
    academic:AcademicSummary
    loans:list[BorrowResponse]
    reservations:list[ReservationResponse]
    overdue_ids:list[int]
    as_of:datetime

@router.get('',response_model=StudentDirectory)
def directory(search:str=Query('',max_length=200),branch:str=Query('',max_length=120),semester:int|None=Query(None,ge=1,le=20),library_id:int|None=Query(None,ge=0),page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    query=db.query(User).filter(User.role==UserRole.STUDENT)
    if search.strip():
        term='%'+search.strip()+'%'
        query=query.filter(User.name.ilike(term)|User.email.ilike(term)|User.student_id.ilike(term))
    if branch:query=query.filter(User.branch==branch)
    if semester is not None:query=query.filter(User.semester==semester)
    if library_id is not None:query=query.filter(User.library_id==library_id if library_id else User.library_id.is_(None))
    return {'items':query.order_by(User.name,User.id).offset((page-1)*page_size).limit(page_size).all(),'total':query.count(),'page':page,'page_size':page_size,
            'branches':[r[0] for r in db.query(User.branch).filter(User.role==UserRole.STUDENT,User.branch.isnot(None),User.branch!='').distinct().order_by(User.branch).all()]}

@router.get('/{student_id}',response_model=StudentDetail)
def detail(student_id:int,db:Session=Depends(get_db)):
    student=db.query(User).filter_by(id=student_id,role=UserRole.STUDENT).first()
    if not student:raise HTTPException(404,'Student not found')
    profile=db.get(AcademicProfile,student_id)
    ids=set(profile.subject_ids or []) if profile else set()
    ids.update(r[0] for r in db.query(SubjectEnrollment.subject_id).filter_by(user_id=student_id))
    subjects=[{'id':n.id,'title':n.title,'source':'curriculum'} for n in db.query(CurriculumNode).filter(CurriculumNode.id.in_(ids),CurriculumNode.kind=='subject').order_by(CurriculumNode.title)] if ids else []
    if profile:
        subjects.extend({'title':title,'source':'custom'} for title in (profile.custom_subjects or []))
    loans=db.query(BorrowRecord).filter_by(user_id=student_id).order_by(BorrowRecord.borrowed_at.desc(),BorrowRecord.id.desc()).all()
    current=database_now(db)
    return {'student':student,'academic':{'college':profile.college if profile else None,'program':profile.program if profile else None,'specialization':profile.specialization if profile else None,'subjects':subjects},
            'loans':loans,'reservations':db.query(Reservation).filter_by(user_id=student_id).order_by(Reservation.created_at.desc(),Reservation.id.desc()).all(),
            'overdue_ids':[l.id for l in loans if l.status=='borrowed' and l.due_date<current],'as_of':current}
