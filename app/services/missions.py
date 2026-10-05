from datetime import datetime,timezone
from app.models.contribution import XPTransaction

def daily_missions(db,user_id,day=None):
    day=day or datetime.now(timezone.utc).date()
    keys={row[0] for row in db.query(XPTransaction.event_key).filter(XPTransaction.user_id==user_id).all()}
    result = [{'id':kind.lower(),'title':title,'xp':25,'completed':f'{kind}:{user_id}:{day.isoformat()}' in keys}
            for kind,title in [('READING','Read Today'),('QUIZ','Complete Chapter Quiz'),('STREAK','Maintain Reading Streak')]]

    from app.models.academic_task import AcademicTask
    from app.models.topic_progress import TopicProgress
    from sqlalchemy import func
    academic=db.query(AcademicTask).filter(AcademicTask.user_id==user_id,func.date(AcademicTask.completed_at)==day).first() is not None
    academic=academic or db.query(TopicProgress).filter(TopicProgress.user_id==user_id,func.date(TopicProgress.completed_at)==day).first() is not None
    result.append({'id':'academic','title':'Study a curriculum topic','xp':0,'completed':academic})
    return result
