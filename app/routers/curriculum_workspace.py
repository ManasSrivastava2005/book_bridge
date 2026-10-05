from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.models.curriculum import Curriculum
from app.models.academic_profile import AcademicProfile
from app.models.student_exam import StudentExam
from app.schemas.personal_curriculum import PersonalNode, PersonalCurriculumWrite
from app.services.personal_curriculum import get_personal, save_personal
from app.services.curriculum_workspace import update_subject
from app.services.curriculum_path import build_path
from app.services.student_curriculum import curriculum_data
from app.routers.student_exams import output as exam_output

router = APIRouter(prefix='/academic', tags=['My Curriculum'])

class AddSubject(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    code: str | None = Field(None, max_length=50)
    semester: int = Field(ge=1, le=20)

class SubjectWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    subject: PersonalNode

class StudyTime(BaseModel):
    model_config = ConfigDict(extra='forbid')
    daily_minutes: int = Field(ge=15, le=720)

@router.get('/workspace')
def workspace(semester:int|None=Query(None,ge=1,le=20), db:Session=Depends(get_db), user:User=Depends(require_role('student'))):
    tree = get_personal(db, user, semester)
    data = curriculum_data(db, user.id, tree['curriculum_id']) if tree['curriculum_id'] else {'subjects': [], 'curriculum': None}
    profile = db.get(AcademicProfile, user.id)
    exams = db.query(StudentExam).filter_by(user_id=user.id).order_by(StudentExam.date, StudentExam.id).all()
    return {'tree': tree, 'subjects': data['subjects'], 'semesters': [c.semester for c in db.query(Curriculum).filter_by(owner_user_id=user.id,archived=False).order_by(Curriculum.semester)],
            'daily_minutes': profile.daily_minutes if profile else 60,
            'exams': [exam_output(db, e) for e in exams],
            'path': build_path(db, user.id, tree['curriculum_id']) if tree['curriculum_id'] else {'steps': [], 'warning': None}}

@router.post('/subjects', status_code=201)
def add_subject(payload:AddSubject, db:Session=Depends(get_db), user:User=Depends(require_role('student'))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    tree = get_personal(db, user, payload.semester)
    tree['subjects'].append(PersonalNode(title=payload.title,code=payload.code).model_dump())
    save_personal(db,user,PersonalCurriculumWrite.model_validate(tree))
    db.commit()
    return get_personal(db,user,payload.semester)

@router.put('/subjects/{subject_id}')
def save_subject(subject_id:int,payload:SubjectWrite,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    subject=update_subject(db,user,subject_id,payload)
    semester=db.get(Curriculum,subject.curriculum_id).semester
    db.commit()
    return get_personal(db,user,semester)

@router.put('/study-time')
def study_time(payload:StudyTime,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    profile=db.get(AcademicProfile,user.id)
    if not profile:
        profile=AcademicProfile(user_id=user.id,subject_ids=[],custom_subjects=[]);db.add(profile)
    profile.daily_minutes=payload.daily_minutes
    db.commit()
    return {'daily_minutes':profile.daily_minutes}

@router.delete('/subjects/{subject_id}/curriculum',status_code=204)
def delete_curriculum(subject_id:int,expected_version:int=Query(ge=1),db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    from app.services.curriculum_workspace import owned_subject
    from app.models.syllabus_upload import SyllabusUpload
    from app.routers.syllabus import mark_deleted,purge_files
    db.query(User).filter_by(id=user.id).with_for_update().one()
    subject=owned_subject(db,user,subject_id)
    curriculum=db.get(Curriculum,subject.curriculum_id)
    tree=get_personal(db,user,curriculum.semester)
    item=next(s for s in tree['subjects'] if s['id']==subject_id)
    item['children']=[]
    update_subject(db,user,subject_id,SubjectWrite(expected_version=expected_version,subject=PersonalNode.model_validate(item)))
    uploads=db.query(SyllabusUpload).filter_by(user_id=user.id,subject_id=subject_id).all()
    for row in uploads:mark_deleted(row)
    db.commit();purge_files(uploads)

@router.delete('/subjects/{subject_id}',status_code=204)
def delete_subject(subject_id:int,expected_version:int=Query(ge=1),db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    from app.services.curriculum_workspace import owned_subject
    from app.models.curriculum import CurriculumNode,SubjectEnrollment
    from app.models.syllabus_upload import SyllabusUpload
    from app.routers.syllabus import mark_deleted,purge_files
    db.query(User).filter_by(id=user.id).with_for_update().one()
    subject=owned_subject(db,user,subject_id)
    curriculum=db.get(Curriculum,subject.curriculum_id)
    if curriculum.version!=expected_version:
        raise HTTPException(409,'Curriculum changed. Reload before deleting this subject.')
    nodes=db.query(CurriculumNode).filter_by(curriculum_id=curriculum.id).all()
    removed={subject_id}
    while True:
        descendants={n.id for n in nodes if n.parent_id in removed}
        if descendants<=removed:break
        removed.update(descendants)
    for node in nodes:
        if node.id in removed:node.archived=True
    curriculum.version+=1
    profile=db.get(AcademicProfile,user.id)
    if profile and profile.curriculum_id==curriculum.id:
        profile.subject_ids=[sid for sid in profile.subject_ids or [] if sid!=subject_id]
    db.query(SubjectEnrollment).filter_by(user_id=user.id,subject_id=subject_id).delete()
    uploads=db.query(SyllabusUpload).filter_by(user_id=user.id,subject_id=subject_id).all()
    for row in uploads:mark_deleted(row)
    db.commit();purge_files(uploads)
