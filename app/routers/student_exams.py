from datetime import date
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict,model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.student_exam import StudentExam
from app.models.academic_profile import AcademicProfile
from app.models.curriculum import CurriculumNode
router=APIRouter(prefix='/academic/exams',tags=['Student exams'])
class ExamWrite(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    subject_id:int|None=Field(None,gt=0)
    custom_subject:str|None=Field(None,min_length=1,max_length=150)
    name:str=Field(min_length=1,max_length=150)
    exam_type:Literal['CAT-I','CAT-II','Midterm','End Semester','Practical','Custom']
    date:date
    topic_ids:list[int]|None=None
    @model_validator(mode='after')
    def subject(self):
        if (self.subject_id is None)==(self.custom_subject is None):raise ValueError('Select exactly one subject')
        return self

def validate_subject(db,user,payload):
    if payload.subject_id:
        from app.services.curriculum_workspace import owned_subject,subject_topic_ids
        from app.models.curriculum import Curriculum
        node=db.get(CurriculumNode,payload.subject_id)
        curriculum=db.get(Curriculum,node.curriculum_id) if node else None
        if curriculum and curriculum.owner_user_id is not None:
            subject=owned_subject(db,user,payload.subject_id)
            valid=subject_topic_ids(db,subject)
            if payload.topic_ids is not None and (len(payload.topic_ids)!=len(set(payload.topic_ids)) or set(payload.topic_ids)-valid):
                raise HTTPException(422,'Choose active topics from this subject only.')
            return
    if payload.topic_ids:
        raise HTTPException(422,'Exam topic coverage requires your personal curriculum subject.')
    profile=db.get(AcademicProfile,user.id)
    if not profile:raise HTTPException(422,'Select your academic subjects first')
    if payload.subject_id and payload.subject_id not in profile.subject_ids:raise HTTPException(422,'Choose one of your selected subjects')
    if payload.custom_subject and payload.custom_subject not in profile.custom_subjects:raise HTTPException(422,'Choose one of your custom subjects')

def output(db,row):
    subject=db.get(CurriculumNode,row.subject_id) if row.subject_id else None
    return {'id':row.id,'subject_id':row.subject_id,'custom_subject':row.custom_subject,'subject':subject.title if subject else row.custom_subject,'name':row.name,'exam_type':row.exam_type,'date':row.date,'topic_ids':row.topic_ids}

@router.get('')
def listing(db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    return [output(db,r) for r in db.query(StudentExam).filter_by(user_id=user.id).order_by(StudentExam.date,StudentExam.id)]
@router.post('',status_code=201)
def create(payload:ExamWrite,db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    validate_subject(db,user,payload)
    row=StudentExam(user_id=user.id,**payload.model_dump());db.add(row);db.commit();return output(db,row)
@router.put('/{exam_id}')
def update(exam_id:int,payload:ExamWrite,db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    row=db.query(StudentExam).filter_by(id=exam_id,user_id=user.id).with_for_update().first()
    if not row:raise HTTPException(404,'Exam not found')
    validate_subject(db,user,payload)
    for k,v in payload.model_dump().items():setattr(row,k,v)
    db.commit();return output(db,row)
@router.delete('/{exam_id}',status_code=204)
def delete(exam_id:int,db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    row=db.query(StudentExam).filter_by(id=exam_id,user_id=user.id).first()
    if not row:raise HTTPException(404,'Exam not found')
    db.delete(row);db.commit()
