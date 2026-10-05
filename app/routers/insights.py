from fastapi import APIRouter,Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.user import User
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.contribution import Contribution
from app.models.resource_usage import ResourceUsage
from app.models.quiz import Quiz
from app.models.curriculum import Curriculum, CurriculumNode

router=APIRouter(prefix='/admin/insights',tags=['Library insights'],dependencies=[Depends(require_role('librarian','admin'))])
@router.get('')
def insights(db:Session=Depends(get_db)):
    now=db.query(func.current_timestamp()).scalar().replace(tzinfo=None)
    active=db.query(BorrowRecord).filter_by(status='borrowed').count()
    overdue=db.query(BorrowRecord).filter(BorrowRecord.status=='borrowed',BorrowRecord.due_date<now).count()
    top_books=db.query(Book.id,Book.title,func.count(BorrowRecord.id).label('count')).join(BorrowRecord).group_by(Book.id,Book.title).order_by(func.count(BorrowRecord.id).desc(),Book.id).limit(10).all()
    top_students=db.query(User.id,User.name,func.count(BorrowRecord.id).label('count')).join(BorrowRecord,BorrowRecord.user_id==User.id).group_by(User.id,User.name).order_by(func.count(BorrowRecord.id).desc(),User.id).limit(10).all()
    demand=db.query(Book.id,Book.title,func.count(Reservation.id).label('count')).join(Reservation).filter(Reservation.status.in_(['pending','ready'])).group_by(Book.id,Book.title).order_by(func.count(Reservation.id).desc(),Book.id).limit(10).all()
    events=db.query(ResourceUsage.resource_kind,func.count(ResourceUsage.id)).group_by(ResourceUsage.resource_kind).all()
    states=dict(db.query(Contribution.status,func.count(Contribution.id)).group_by(Contribution.status).all())
    paper_ids=db.query(Contribution.question_bank_id).filter(Contribution.kind=='question_paper',Contribution.status=='APPROVED',Contribution.question_bank_id.isnot(None))
    return {'as_of':now,'scope':'All libraries; lifetime recorded totals unless labelled otherwise',
        'active_loans':active,'overdue_loans':overdue,'current_overdue_rate':round(overdue/active*100,1) if active else 0,
        'top_books':[{'id':r.id,'title':r.title,'count':r.count} for r in top_books],
        'top_students':[{'id':r.id,'name':r.name,'count':r.count} for r in top_students],
        'reservation_demand':[{'id':r.id,'title':r.title,'count':r.count} for r in demand],
        'download_requests':dict(events),'tracking_first_event':db.query(func.min(ResourceUsage.created_at)).scalar(),
        'note_download_counter':db.query(func.coalesce(func.sum(Note.download_count),0)).filter(Note.status=='published').scalar(),
        'question_bank_download_counter':db.query(func.coalesce(func.sum(QuestionBank.download_count),0)).scalar(),
        'approved_question_paper_download_counter':db.query(func.coalesce(func.sum(QuestionBank.download_count),0)).filter(QuestionBank.id.in_(paper_ids)).scalar(),
        'contributions':{s:states.get(s,0) for s in ('PENDING','APPROVED','REJECTED')},
        'published_quizzes':db.query(Quiz).filter_by(status='published').count(),
        'quiz_participation':None,'quiz_average_score':None,'reading_time':None,
        'limitations':['Download events count requests, not completed transfers or unique readers.',
                      'Direct public-file and external-site downloads cannot be observed.',
                      'Legacy question resources lack a reliable paper/bank distinction; paper totals include approved paper contributions only.',
                      'Quiz attempts and validated reading time are not collected yet.']}
