import uuid
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel,Field,ConfigDict,StrictInt
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.models.quiz import Quiz,QuizQuestion
from app.models.book import Book
from app.models.curriculum import CurriculumNode
from app.models.quiz_attempt import QuizAttempt
from app.models.contribution import XPTransaction
router=APIRouter(prefix='/student/quizzes',tags=['Student quizzes'])
def student():return Depends(require_role('student'))
def now_utc():return datetime.now(timezone.utc).replace(tzinfo=None)

def visible(db,quiz_id):
    quiz=db.query(Quiz).filter_by(id=quiz_id,status='published',active=True,permission_confirmed=True).with_for_update().first()
    if not quiz:raise HTTPException(404,'Published quiz not available')
    return quiz

def result(row):
    data={'attempt_id':row.id,'quiz_id':row.quiz_id,'title':row.title,'score':row.score,'submitted_at':row.submitted_at,'questions':[{'position':i,'prompt':q['prompt'],'options':q['options']} for i,q in enumerate(row.questions)]}
    if row.submitted_at:
        data['answers']=row.answers;data['review']=[{'correct_index':q['correct_index'],'explanation':q['explanation']} for q in row.questions]
    return data

@router.get('')
def listing(db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    rows=[]
    for q in db.query(Quiz).filter_by(status='published',active=True,permission_confirmed=True).order_by(Quiz.id):
        book=db.get(Book,q.book_id) if q.book_id else None
        subject=db.get(CurriculumNode,q.subject_id) if q.subject_id else None
        topic=db.get(CurriculumNode,q.topic_id) if q.topic_id else None
        rows.append({'id':q.id,'title':q.title,'subject_id':q.subject_id,'topic_id':q.topic_id,'book_id':q.book_id,'chapter':q.chapter,'book_title':book.title if book else None,'subject':subject.title if subject else None,'topic':topic.title if topic else None})
    return rows

@router.get('/attempts')
def attempts(db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    return [{'attempt_id':r.id,'quiz_id':r.quiz_id,'title':r.title,'score':r.score,'submitted_at':r.submitted_at} for r in db.query(QuizAttempt).filter_by(user_id=user.id).order_by(QuizAttempt.started_at.desc()).limit(100)]

@router.post('/{quiz_id}/start')
def start(quiz_id:int,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    quiz=visible(db,quiz_id)
    existing=db.query(QuizAttempt).filter_by(user_id=user.id,quiz_id=quiz_id,submitted_at=None).first()
    if existing:return result(existing)
    questions=db.query(QuizQuestion).filter_by(quiz_id=quiz_id).order_by(QuizQuestion.position).all()
    if len(questions)!=10:raise HTTPException(409,'This quiz requires ten published questions')
    row=QuizAttempt(id=str(uuid.uuid4()),user_id=user.id,quiz_id=quiz.id,title=quiz.title,book_id=quiz.book_id,subject_id=quiz.subject_id,topic_id=quiz.topic_id,chapter=quiz.chapter,started_at=now_utc(),questions=[{'prompt':q.prompt,'options':q.options,'correct_index':q.correct_index,'explanation':q.explanation} for q in questions])
    db.add(row);db.commit();return result(row)

class Submission(BaseModel):
    model_config=ConfigDict(extra='forbid')
    answers:list[StrictInt]=Field(min_length=10,max_length=10)

@router.post('/attempts/{attempt_id}/submit')
def submit(attempt_id:str,payload:Submission,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    row=db.query(QuizAttempt).filter_by(id=attempt_id,user_id=user.id).with_for_update().first()
    if not row:raise HTTPException(404,'Attempt not found')
    if row.submitted_at:
        if row.answers!=payload.answers:raise HTTPException(409,'This attempt was already submitted')
        return result(row)
    visible(db,row.quiz_id)
    if any(answer<0 or answer>=len(question['options']) for answer,question in zip(payload.answers,row.questions)):raise HTTPException(422,'Select a valid option for every question')
    row.answers=payload.answers;row.score=10*sum(answer==q['correct_index'] for answer,q in zip(payload.answers,row.questions));row.submitted_at=now_utc()
    key=f'QUIZ:{user.id}:{row.submitted_at.date().isoformat()}'
    if not db.query(XPTransaction).filter_by(event_key=key).first():db.add(XPTransaction(user_id=user.id,amount=25,event_type='QUIZ',event_key=key,description='Completed a chapter quiz',created_at=row.submitted_at))
    db.flush()
    from app.services.badges import award_badges
    award_badges(db,user.id);db.commit();return result(row)

@router.get('/attempts/{attempt_id}')
def attempt(attempt_id:str,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    row=db.query(QuizAttempt).filter_by(id=attempt_id,user_id=user.id).first()
    if not row:raise HTTPException(404,'Attempt not found')
    return result(row)
