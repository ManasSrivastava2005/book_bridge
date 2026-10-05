from fastapi import HTTPException
from app.models.academic_profile import AcademicProfile
from app.models.curriculum import Curriculum,CurriculumNode

def save_profile(db,user,payload):
    if payload.curriculum_id:
        curriculum=db.get(Curriculum,payload.curriculum_id)
        if not curriculum or curriculum.archived or curriculum.owner_user_id not in (None,user.id):raise HTTPException(422,'Select an active curriculum')
        valid={n.id for n in db.query(CurriculumNode).filter_by(curriculum_id=curriculum.id,kind='subject',archived=False)}
        if not set(payload.subject_ids)<=valid:raise HTTPException(422,'Subjects must belong to the selected curriculum')
    elif payload.subject_ids:raise HTTPException(422,'Select a curriculum before its subjects')
    row=db.get(AcademicProfile,user.id)
    if not row:row=AcademicProfile(user_id=user.id);db.add(row)
    from app.services.student_curriculum import sync_enrollment
    sync_enrollment(db,user.id,row.subject_ids or [],payload.subject_ids)
    for key,value in payload.model_dump(exclude={'branch','semester'}).items():setattr(row,key,value)
    user.branch=payload.branch or None;user.semester=payload.semester
    return row
