from datetime import datetime,timezone
from fastapi import APIRouter,Depends,Query,HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.models.academic_task import AcademicTask
from app.models.topic_progress import TopicProgress
from app.services.academic_plan import generate_plan
from app.services.student_curriculum import selected_topic
router=APIRouter(prefix='/academic/plan',tags=['Academic plan'])
@router.get('')
def plan(daily_minutes:int=Query(120,ge=30,le=480),db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    result=generate_plan(db,user.id,daily_minutes);db.commit();return result
@router.put('/tasks/{task_id}')
def complete(task_id:int,completed:bool,db:Session=Depends(get_db),user:User=Depends(require_role("student"))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    row=db.query(AcademicTask).filter_by(id=task_id,user_id=user.id).first()
    if not row:raise HTTPException(404,'Task not found')
    selected_topic(db,user.id,row.topic_id)
    if row.kind=='quiz':raise HTTPException(409,'Complete the quiz to finish this task')
    row.completed_at=datetime.now(timezone.utc).replace(tzinfo=None) if completed else None
    if row.kind in ('read','practice'):
        topic=db.get(TopicProgress,(user.id,row.topic_id))
        if completed and not topic:db.add(TopicProgress(user_id=user.id,topic_id=row.topic_id))
        if not completed and topic:db.delete(topic)
    db.flush()
    from app.services.badges import award_badges
    award_badges(db,user.id);db.commit()
    return {'completed':completed}
