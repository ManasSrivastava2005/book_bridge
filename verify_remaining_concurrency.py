"""Temporary PostgreSQL fixtures verify concurrent collaboration and reminders."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import uuid
import httpx
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User,UserRole
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.notification import Notification
from app.models.overdue_reminder import OverdueReminder
from app.models.study import StudyRoom,StudyMember,StudyMessage,StudyAudit,StudyReport
from app.routers.admin import database_now
from app.services.auth import create_access_token

marker='Concurrent verification '+uuid.uuid4().hex[:10]
rid=bid=loan_id=None
with SessionLocal() as db:
 users=db.query(User).filter(User.role==UserRole.STUDENT).order_by(User.id).limit(2).all()
 tokens=[create_access_token(u.id,u.role.value) for u in users];owner_id=users[0].id

def request(index,method,path,**kwargs):
 with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+tokens[index]},timeout=15) as client:
  return client.request(method,path,**kwargs)
try:
 response=request(0,'POST','/study/rooms',json={'title':marker,'subject':'Concurrency','is_private':True})
 assert response.status_code==201,response.text
 room=response.json();rid=room['id']
 assert request(1,'POST',f'/study/rooms/{rid}/join',params={'invite':room['invite_code']}).status_code==200
 for turn in range(3):
  def post(index):return request(index,'POST',f'/study/rooms/{rid}/messages',json={'body':f'Fixture {turn}-{index}','client_id':str(uuid.uuid4())})
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(post,[0,1]))
  assert all(r.status_code==201 for r in results),[r.status_code for r in results]
 key=str(uuid.uuid4())
 def retry(_):return request(0,'POST',f'/study/rooms/{rid}/messages',json={'body':'Concurrent retry','client_id':key})
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(retry,range(2)))
 assert all(r.status_code==201 for r in results)
 assert results[0].json()==results[1].json()
 with SessionLocal() as db:
  assert db.query(StudyMessage).filter(StudyMessage.room_id==rid).count()==7
  book=Book(title=marker,author='Verification fixture');db.add(book);db.flush();bid=book.id
  loan=BorrowRecord(user_id=owner_id,book_id=bid,status='borrowed',due_date=database_now(db)-timedelta(days=2));db.add(loan);db.flush();loan_id=loan.id;db.commit()
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:request(0,'GET','/notifications/unread-count'),range(2)))
 assert all(r.status_code==200 for r in results)
 with SessionLocal() as db:
  assert db.query(OverdueReminder).filter(OverdueReminder.borrow_id==loan_id).count()==1
 print('Concurrent posts by two accounts, duplicate post retries, and daily reminder deduplication: passed')
finally:
 with SessionLocal() as db:
  if rid:
   for model in (StudyReport,StudyAudit,StudyMessage,StudyMember):db.query(model).filter(model.room_id==rid).delete(synchronize_session=False)
   db.query(StudyRoom).filter(StudyRoom.id==rid,StudyRoom.title==marker).delete(synchronize_session=False)
  if loan_id:
   notice_ids=[r.notification_id for r in db.query(OverdueReminder).filter(OverdueReminder.borrow_id==loan_id).all()]
   db.query(OverdueReminder).filter(OverdueReminder.borrow_id==loan_id).delete(synchronize_session=False)
   db.query(Notification).filter(Notification.id.in_(notice_ids)).delete(synchronize_session=False)
   db.query(BorrowRecord).filter(BorrowRecord.id==loan_id,BorrowRecord.book_id==bid).delete(synchronize_session=False)
  if bid:db.query(Book).filter(Book.id==bid,Book.title==marker).delete(synchronize_session=False)
  db.query(Notification).filter(Notification.message=='New discussion in Study Together: '+marker).delete(synchronize_session=False)
  db.commit()
