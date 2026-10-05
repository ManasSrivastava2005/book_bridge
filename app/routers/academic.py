from fastapi import APIRouter,Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role, bearer_scheme
from app.models.user import User
from app.models.academic_profile import AcademicProfile
from app.models.curriculum import Curriculum,CurriculumNode
from app.schemas.academic import AcademicWrite
from app.services.academic import save_profile
router=APIRouter(prefix='/academic',tags=['Academic profile'])

@router.get('/catalog')
def catalog(db:Session=Depends(get_db),credentials:HTTPAuthorizationCredentials|None=Depends(bearer_scheme)):
    user=get_current_user(credentials,db) if credentials else None
    rows=db.query(Curriculum).filter(Curriculum.archived.is_(False),or_(Curriculum.owner_user_id.is_(None),Curriculum.owner_user_id==user.id) if user and user.role.value=="student" else Curriculum.owner_user_id.is_(None)).order_by(Curriculum.college,Curriculum.title,Curriculum.version.desc()).all()
    return [{'id':r.id,'title':r.title,'college':r.college,'program':r.program,'branch':r.branch,'specialization':r.specialization,'semester':r.semester,'version':r.version,'subjects':[{'id':n.id,'title':n.title} for n in db.query(CurriculumNode).filter_by(curriculum_id=r.id,kind='subject').order_by(CurriculumNode.position,CurriculumNode.id)]} for r in rows]

@router.get('/profile')
def profile(db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    row=db.get(AcademicProfile,user.id)
    values={k:getattr(row,k) for k in ('college','program','specialization','curriculum_id','subject_ids','custom_subjects','goals')} if row else AcademicWrite().model_dump(exclude={'branch','semester'})
    return {**values,'branch':user.branch,'semester':user.semester}

@router.put('/profile')
def update(payload:AcademicWrite,db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    save_profile(db,user,payload);db.flush()
    from app.services.badges import award_badges
    award_badges(db,user.id);db.commit()
    return profile(db,user)

@router.get('/curriculum')
def my_curriculum(db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    from app.services.student_curriculum import curriculum_data
    return curriculum_data(db,user.id)

@router.put('/topics/{topic_id}/completion')
def complete_topic(topic_id:int,completed:bool,db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    from app.models.topic_progress import TopicProgress
    from app.services.student_curriculum import selected_topic
    from app.services.badges import award_badges
    db.query(User).filter_by(id=user.id).with_for_update().one()
    selected_topic(db,user.id,topic_id)
    row=db.get(TopicProgress,(user.id,topic_id))
    if completed and not row:db.add(TopicProgress(user_id=user.id,topic_id=topic_id))
    if not completed and row:db.delete(row)
    db.flush();award_badges(db,user.id);db.commit()
    return my_curriculum(db,user)

@router.get('/learning-path')
def learning_path(db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    from app.services.curriculum_path import build_path
    return build_path(db,user.id)
