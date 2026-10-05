"""Idempotent badges based on persisted records; badges do not grant extra XP."""
from sqlalchemy import func
from app.models.review import Review
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models.badge import Badge, UserBadge
from app.models.user import User
from app.models.borrow import BorrowRecord
from app.models.reading_session import ReadingDay, ReadingSession
from app.models.reading_activity import ReadingActivity
from app.models.topic_progress import TopicProgress
from app.models.academic_task import AcademicTask
from app.models.quiz import Quiz,QuizQuestion
from app.models.student_exam import StudentExam
from app.models.quiz_attempt import QuizAttempt
from app.models.academic_profile import AcademicProfile
from app.models.curriculum import Curriculum,CurriculumNode,CurriculumResource,SubjectEnrollment
from app.models.contribution import Contribution
from app.services.xp import reader_level

RULES = [(name,'borrow',n,f'Borrow {n} distinct book titles.') for name,n in [('First Borrow',1),('Book Explorer',5),('Bibliophile',10),('Scholar',25),('Library Legend',50)]]
RULES += [(f'{n}-Day Streak','streak',n,f'Qualify for reading on {n} consecutive days.') for n in (3,7,14,30,100)]
RULES += [(name,'level',n,f'Reach reader level {n}.') for name,n in [('Bronze Reader',5),('Silver Scholar',10),('Gold Scholar',20),('Knowledge Master',35),('Book Bridge Legend',50)]]
RULES += [('Contributor','contribution',1,'Have one approved contribution.'),('Exam Helper','paper',1,'Have one approved question paper.'),('Knowledge Sharer','contribution',5,'Have five approved contributions.'),('Community Scholar','contribution',20,'Have twenty approved contributions.')]
RULES += [('Quiz Starter','quiz',1,'Complete one persisted chapter quiz.'),('Sharp Mind','high_quiz',5,'Score at least 80% on five distinct quizzes.'),('Perfect Chapter','perfect',1,'Score 100% on a chapter quiz.'),('Quiz Scholar','quiz',20,'Complete twenty distinct chapter quizzes.')]
RULES += [('Path Finder','curriculum',1,'Enroll in a curriculum subject.'),('Quarter Master','progress',25,'Complete 25% of a selected subject.'),('Halfway There','progress',50,'Complete 50% of a selected subject.'),('Subject Master','progress',100,'Complete all topics in a selected subject.'),('Exam Ready','exam_ready',1,'Complete all topics for an upcoming exam subject.')]

RULES += [('Reviewer','review',5,'Write reviews for 5 distinct books with verified borrowing history.')]

def insert_for(db):return pg_insert if db.get_bind().dialect.name=='postgresql' else sqlite_insert

def seed_badges(db):
    for name,kind,threshold,description in RULES:
        db.execute(insert_for(db)(Badge).values(name=name,description=description,icon='award',xp_reward=0).on_conflict_do_nothing(index_elements=['name']))

def badge_metrics(db,user_id):
    from app.routers.reading_activity import streak_data
    contributions=db.query(Contribution).filter_by(user_id=user_id,status='APPROVED')
    metrics={'borrow':db.query(func.count(func.distinct(BorrowRecord.book_id))).filter(BorrowRecord.user_id==user_id).scalar(),
             'streak':streak_data(db,user_id)['longest_streak'], 'level':reader_level(db,user_id)['level'],
             'contribution':contributions.count(),'paper':contributions.filter_by(kind='question_paper').count()}
    from app.services.student_curriculum import curriculum_data
    subjects=curriculum_data(db,user_id)["subjects"]
    metrics["curriculum"]=len(subjects)
    metrics["progress"]=max((s["progress_percent"] for s in subjects),default=0)
    from datetime import datetime, timezone
    ready={s["id"] for s in subjects if s["total_topics"] and s["progress_percent"]==100}
    metrics["exam_ready"]=db.query(StudentExam).filter(StudentExam.user_id==user_id,StudentExam.subject_id.in_(ready),StudentExam.date>=datetime.now(timezone.utc).date()).count() if ready else 0
    attempts=db.query(QuizAttempt).filter(QuizAttempt.user_id==user_id,QuizAttempt.submitted_at.isnot(None))
    metrics["quiz"]=attempts.with_entities(func.count(func.distinct(QuizAttempt.quiz_id))).scalar()
    metrics["high_quiz"]=attempts.filter(QuizAttempt.score>=80).with_entities(func.count(func.distinct(QuizAttempt.quiz_id))).scalar()
    metrics["perfect"]=attempts.filter(QuizAttempt.score==100).count()
    from app.models.review import Review
    eligible=db.query(BorrowRecord.book_id).filter(BorrowRecord.user_id==user_id,BorrowRecord.status.in_(['borrowed','returned']))
    metrics['review']=db.query(func.count(func.distinct(Review.book_id))).filter(Review.user_id==user_id,Review.book_id.in_(eligible),Review.comment.isnot(None),func.length(func.trim(Review.comment))>0).scalar()
    return metrics

def award_badges(db,user_id):
    user=db.query(User).filter(User.id==user_id).with_for_update().one()
    if user.role.value!='student':return
    metrics=badge_metrics(db,user_id)
    definitions={b.name:b.id for b in db.query(Badge).all()}
    for name,kind,threshold,description in RULES:
        if name in definitions and metrics.get(kind,0)>=threshold:
            db.execute(insert_for(db)(UserBadge).values(user_id=user_id,badge_id=definitions[name]).on_conflict_do_nothing(index_elements=['user_id','badge_id']))
