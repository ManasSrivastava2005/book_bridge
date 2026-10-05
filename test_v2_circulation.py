"""V2 staff circulation contract and inventory regressions, isolated SQLite."""
from datetime import datetime, timedelta
from uuid import uuid4
from test_staff_operations import StaffTests
from app.models.book import Book
from app.models.user import User
from app.models.library import Library
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.notification import Notification


class CirculationV2Tests(StaffTests):
 def test_staff_only_idempotent_checkout_and_return(self):
  payload={'student_id':2,'book_id':1,'request_id':str(uuid4())}
  self.assertEqual(self.client.post('/borrows/',headers=self.student,json={'book_id':1}).status_code,403)
  self.assertEqual(self.client.post('/admin/loans',headers=self.student,json=payload).status_code,403)
  first=self.client.post('/admin/loans',headers=self.staff,json=payload)
  self.assertEqual(first.status_code,201,first.text)
  retry=self.client.post('/admin/loans',headers=self.staff,json=payload)
  self.assertEqual(retry.json()['id'],first.json()['id'])
  self.assertEqual(self.client.post('/admin/loans',headers=self.staff,json={**payload,'student_id':3}).status_code,409)
  self.assertEqual(self.client.post(f"/borrows/{first.json()['id']}/return",headers=self.student).status_code,403)
  for _ in range(2):
   self.assertEqual(self.client.post(f"/borrows/{first.json()['id']}/return",headers=self.staff).status_code,200)
  self.assertEqual(self.copies(),1)
  with self.factory() as db:
   self.assertEqual(db.query(BorrowRecord).count(),1)
   self.assertEqual(db.query(Notification).count(),2)
   self.assertEqual(db.query(BorrowRecord).one().issued_by,1)

 def test_library_membership_due_date_and_search(self):
  with self.factory() as db:
   db.add(Library(name='Main',code='MAIN',campus='Test'));db.flush()
   db.get(Book,1).library_id=1;db.get(User,2).student_id='CSE2026';db.commit()
  payload={'student_id':2,'book_id':1,'library_id':1}
  self.assertEqual(self.client.post('/admin/loans',headers=self.staff,json=payload).status_code,403)
  with self.factory() as db:db.get(User,2).library_id=1;db.commit()
  self.assertEqual(self.client.post('/admin/loans',headers=self.staff,json={**payload,'library_id':99}).status_code,422)
  for due in [datetime.now()-timedelta(days=1),datetime.now()+timedelta(days=400)]:
   self.assertEqual(self.client.post('/admin/loans',headers=self.staff,json={**payload,'due_date':due.isoformat()}).status_code,422)
  due=(datetime.now()+timedelta(days=7)).replace(microsecond=0).isoformat()
  response=self.client.post('/admin/loans',headers=self.staff,json={**payload,'due_date':due})
  self.assertEqual(response.status_code,201,response.text);self.assertEqual(response.json()['due_date'],due)
  result=self.client.get('/admin/students?search=cse2026',headers=self.staff).json()
  self.assertEqual([u['id'] for u in result],[2])

 def test_ready_queue_fulfillment_keeps_history(self):
  with self.factory() as db:
   db.add_all([Reservation(user_id=2,book_id=1,status='pending'),Reservation(user_id=3,book_id=1,status='pending')]);db.commit()
  self.assertEqual(self.client.post('/admin/reservations/2/ready',headers=self.staff).status_code,409)
  self.assertEqual(self.client.post('/admin/reservations/1/ready',headers=self.student).status_code,403)
  for _ in range(2):
   self.assertEqual(self.client.post('/admin/reservations/1/ready',headers=self.staff).status_code,200)
  self.assertEqual(self.copies(),0)
  loan=self.client.post('/admin/loans',headers=self.staff,json={'student_id':2,'book_id':1})
  self.assertEqual(loan.status_code,201,loan.text)
  self.assertEqual(self.client.post('/admin/reservations/1/release',headers=self.staff).status_code,409)
  self.client.post(f"/borrows/{loan.json()['id']}/return",headers=self.staff)
  with self.factory() as db:
   first=db.get(Reservation,1);second=db.get(Reservation,2)
   self.assertEqual(first.status,'fulfilled');self.assertEqual(first.loan_id,loan.json()['id'])
   self.assertIsNotNone(first.fulfilled_at);self.assertIsNotNone(first.ready_at)
   self.assertEqual(second.status,'ready');self.assertIsNotNone(second.ready_at)
  self.assertEqual(self.copies(),0)
