from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.badge import Badge,UserBadge
from app.services.badges import award_badges,RULES,badge_metrics
router=APIRouter(prefix='/badges',tags=['Badges'])
@router.get('/my')
def badges(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    award_badges(db,user.id);db.commit()
    owned={b.badge_id:b.earned_at for b in db.query(UserBadge).filter_by(user_id=user.id)}
    rules={name:description for name,kind,threshold,description in RULES}
    return [{'id':b.id,'name':b.name,'description':rules.get(b.name,b.description),'earned':b.id in owned,'earned_at':owned.get(b.id)} for b in db.query(Badge).order_by(Badge.id)]


@router.get('/achievements')
def achievements(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    from app.services.xp import reader_level
    from app.routers.reading_activity import streak_data
    award_badges(db,user.id);db.commit()
    metrics=badge_metrics(db,user.id)
    owned={b.badge_id:b.earned_at for b in db.query(UserBadge).filter_by(user_id=user.id)}
    rules={name:(kind,threshold,description) for name,kind,threshold,description in RULES}
    categories={'borrow':('Reading','books'),'streak':('Streak','days'),'level':('Level','levels'),'contribution':('Contribution','contributions'),'paper':('Contribution','papers'),'quiz':('Quiz','quizzes'),'high_quiz':('Quiz','qualifying quizzes'),'perfect':('Quiz','perfect scores'),'curriculum':('Curriculum','subjects'),'progress':('Curriculum','%'),'exam_ready':('Curriculum','subjects'),'review':('Other','reviews')}
    items=[]
    for badge in db.query(Badge).order_by(Badge.id):
        rule=rules.get(badge.name)
        kind,target,description=rule if rule else (None,None,badge.description)
        category,unit=categories.get(kind,('Other',''))
        value=metrics.get(kind) if rule else None
        items.append({'id':badge.id,'name':badge.name,'description':description,'category':category,'unit':unit,'current':value,'target':target,'earned':badge.id in owned,'earned_at':owned.get(badge.id),'unlock_xp':0,'tracking_available':value is not None})
    return {'reader':reader_level(db,user.id),'current_streak':streak_data(db,user.id)['current_streak'],'badges':items}
