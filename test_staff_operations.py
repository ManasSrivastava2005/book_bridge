"""Isolated staff operations tests; never seeds or modifies the live database."""
import unittest
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from unittest.mock import patch
from app.models.review import Review
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.library import Library
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.routers import admin, borrows, reservations, digital_resources
from app.services.auth import create_access_token

class StaffTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
  Base.metadata.create_all(self.engine);self.factory=sessionmaker(bind=self.engine)
  with self.factory() as db:
   for i,role in enumerate([UserRole.LIBRARIAN,UserRole.STUDENT,UserRole.STUDENT,UserRole.ADMIN]):
    db.add(User(name=f'Test {i+1}',email=f'test{i+1}@example.com',hashed_password='unused',role=role))
   db.add(Book(title='OS fixture',author='Author',total_copies=1,available_copies=1))
   db.commit()
  def dependency():
   with self.factory() as db:yield db
  app=FastAPI()
  for router in [admin.router,borrows.router,reservations.router,digital_resources.router]:app.include_router(router)
  app.dependency_overrides[get_db]=dependency
  self.client=TestClient(app);self.addCleanup(self.client.close);self.addCleanup(self.engine.dispose)
  self.staff=self.headers(1,'librarian');self.student=self.headers(2,'student');self.waiting=self.headers(3,'student')
 def headers(self,id,role):return {'Authorization':'Bearer '+create_access_token(id,role)}
 def copies(self):
  with self.factory() as db:return db.get(Book,1).available_copies
 def test_staff_endpoints_require_jwt_and_role(self):
  for path in ['/admin/dashboard','/admin/analytics','/admin/metrics','/admin/students','/admin/overdue-books','/admin/reservations','/admin/digital-resources']:
   with self.subTest(path=path):
    self.assertEqual(self.client.get(path).status_code,401)
    self.assertEqual(self.client.get(path,headers=self.student).status_code,403)
    self.assertEqual(self.client.get(path,headers=self.staff).status_code,200)
  self.assertEqual(self.client.post('/admin/seed',headers=self.staff).status_code,403)
  self.assertEqual(self.client.post('/admin/loans',headers=self.student,json={'student_id':2,'book_id':1}).status_code,403)
 def test_metrics_overdue_and_students_contract(self):
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,due_date=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=2),status='borrowed'))
   db.get(Book,1).available_copies=0;db.commit()
  response=self.client.get('/admin/dashboard',headers=self.staff)
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json()['metrics']['overdue_books'],1)
  self.assertTrue(response.json()['recent_activities'][0]['is_overdue'])
  self.assertEqual(len(self.client.get('/admin/overdue-books',headers=self.staff).json()),1)
  students=self.client.get('/admin/students',headers=self.staff).json()
  self.assertEqual(len(students),2);self.assertNotIn('hashed_password',students[0])
 def test_dashboard_empty_and_held_reservations(self):
  with self.factory() as db:
   db.add(Reservation(user_id=2,book_id=1,status='ready'))
   db.add(Reservation(user_id=3,book_id=1,status='pending'));db.commit()
  data=self.client.get('/admin/dashboard',headers=self.staff).json()
  self.assertEqual(data['metrics']['reservations'],2)
  self.assertEqual(data['metrics']['total_books'],1)
  self.assertEqual(data['recent_books'][0]['title'],'OS fixture')
  with self.factory() as db:
   db.query(Reservation).delete();db.query(Book).delete();db.commit()
  data=self.client.get('/admin/dashboard',headers=self.staff).json()
  self.assertEqual(data['recent_books'],[])
  self.assertEqual(data['metrics']['total_copies'],0)
 def test_checkout_return_queue_and_held_checkout(self):
  first=self.client.post('/admin/loans',headers=self.staff,json={'student_id':2,'book_id':1})
  self.assertEqual(first.status_code,201);self.assertEqual(self.copies(),0)
  self.assertEqual(self.client.post('/admin/loans',headers=self.staff,json={'student_id':2,'book_id':1}).status_code,409)
  held=self.client.post('/reservations/',headers=self.waiting,json={'book_id':1})
  self.assertEqual(held.status_code,201)
  self.assertEqual(self.client.post(f'/borrows/{first.json()["id"]}/return',headers=self.waiting).status_code,403)
  self.assertEqual(self.client.post(f'/borrows/{first.json()["id"]}/return',headers=self.staff).status_code,200)
  self.assertEqual(self.copies(),0)
  self.assertEqual(self.client.get('/admin/reservations',headers=self.staff).json()[0]['status'],'ready')
  self.assertEqual(self.client.post(f'/borrows/{first.json()["id"]}/return',headers=self.staff).status_code,200)
  second=self.client.post('/admin/loans',headers=self.staff,json={'student_id':3,'book_id':1})
  self.assertEqual(second.status_code,201);self.assertEqual(self.copies(),0)
  history=self.client.get('/admin/reservations',headers=self.staff).json()
  self.assertEqual(history[0]['status'],'fulfilled');self.assertEqual(history[0]['loan_id'],second.json()['id'])
  self.assertEqual(self.client.post(f'/borrows/{second.json()["id"]}/return',headers=self.staff).status_code,200)
  self.assertEqual(self.copies(),1)
 def test_release_moves_copy_to_next_student_then_inventory(self):
  with self.factory() as db:
   db.get(Book,1).available_copies=0
   db.add(Reservation(user_id=2,book_id=1,status='ready'));db.add(Reservation(user_id=3,book_id=1,status='pending'));db.commit()
  self.assertEqual(self.client.post('/admin/reservations/1/release',headers=self.student).status_code,403)
  self.assertEqual(self.client.post('/admin/reservations/1/release',headers=self.staff).status_code,200)
  self.assertEqual(self.copies(),0)
  self.assertEqual(self.client.post('/admin/reservations/1/release',headers=self.staff).status_code,200)
  self.assertEqual(self.client.post('/admin/reservations/2/release',headers=self.staff).status_code,200)
  self.assertEqual(self.copies(),1)
 def test_pending_cancellation_and_invalid_student(self):
  with self.factory() as db:
   db.get(Book,1).available_copies=0;db.add(Reservation(user_id=2,book_id=1,status='pending'));db.commit()
  self.assertEqual(self.client.delete('/reservations/1',headers=self.waiting).status_code,403)
  self.assertEqual(self.client.delete('/reservations/1',headers=self.staff).status_code,204)
  self.assertEqual(self.copies(),0)
  self.assertEqual(self.client.post('/admin/loans',headers=self.staff,json={'student_id':1,'book_id':1}).status_code,404)
 def test_resource_draft_publish_and_validation(self):
  payload={'title':'Digital fixture','author':'Author','library_id':None,'file_url':'/uploads/ebooks/fixture.pdf','is_published':False,'distribution_basis':'permission','license_name':'Fixture permission','rights_evidence':'Original acceptance fixture permitted for testing.'}
  created=self.client.post('/digital-resources/',headers=self.staff,json=payload)
  self.assertEqual(created.status_code,201)
  rid=created.json()['id']
  self.assertEqual(self.client.get('/digital-resources/').json(),[])
  self.assertEqual(self.client.get(f'/digital-resources/{rid}',headers=self.student).status_code,404)
  self.assertEqual(self.client.get(f'/digital-resources/{rid}').status_code,404)
  self.assertEqual(self.client.get(f'/digital-resources/{rid}',headers=self.staff).status_code,200)
  self.assertEqual(len(self.client.get('/admin/digital-resources',headers=self.staff).json()),1)
  self.assertEqual(self.client.put(f'/admin/digital-resources/{rid}',headers=self.student,json=payload).status_code,403)
  self.assertEqual(self.client.put(f'/admin/digital-resources/{rid}',headers=self.staff,json={**payload,'is_published':True}).status_code,200)
  self.assertEqual(len(self.client.get('/digital-resources/').json()),1)
  for bad in ['javascript:alert(1)','file:///C:/secret','/uploads/../private','https://user:pass@example.com/a']:
   self.assertEqual(self.client.put(f'/admin/digital-resources/{rid}',headers=self.staff,json={**payload,'file_url':bad}).status_code,422)
  self.assertEqual(self.client.put(f'/admin/digital-resources/{rid}',headers=self.staff,json={**payload,'library_id':999}).status_code,404)

 def test_analytics_calendar_boundaries_library_scope_and_overdue_ages(self):
  now=datetime(2026,9,19,12,0,0)
  start=datetime(2026,9,13)
  with self.factory() as db:
   library=Library(name='Main',code='MAIN',campus='Campus');db.add(library);db.flush();lid=library.id
   db.get(Book,1).library_id=lid;db.get(Book,1).category='CS'
   second=Book(title='Other branch',author='Author',category='Other');db.add(second);db.flush()
   for borrowed,due,returned,status,book_id in [
    (start,now-timedelta(days=1),None,'borrowed',1),
    (start-timedelta(seconds=1),now-timedelta(days=7),None,'borrowed',1),
    (now-timedelta(days=40),now-timedelta(days=30),None,'borrowed',1),
    (now-timedelta(days=40),now-timedelta(days=31),start,'returned',1),
    (now,now+timedelta(days=14),None,'borrowed',1),
    (now+timedelta(seconds=1),now+timedelta(days=14),None,'borrowed',1),
    (now,now-timedelta(days=2),None,'borrowed',second.id),
   ]:
    db.add(BorrowRecord(user_id=2,book_id=book_id,borrowed_at=borrowed,due_date=due,returned_at=returned,status=status))
   db.commit()
  with patch.object(admin,'database_now',return_value=now):
   response=self.client.get(f'/admin/analytics?days=7&library_id={lid}',headers=self.staff)
   self.assertEqual(response.status_code,200,response.text);data=response.json()
   self.assertEqual(data['period']['start'],'2026-09-13');self.assertEqual(data['period']['end'],'2026-09-19')
   self.assertEqual(len(data['daily']),7)
   self.assertEqual(data['totals'],{'checkouts':2,'returns':1,'unique_borrowers':1})
   self.assertEqual(data['daily'][0],{'date':'2026-09-13','checkouts':1,'returns':1})
   self.assertEqual(data['daily'][1]['checkouts'],0)
   self.assertEqual([row['count'] for row in data['overdue']],[1,1,1])
   self.assertEqual(data['categories'],[{'category':'CS','checkouts':2}])
   all_data=self.client.get('/admin/analytics?days=7',headers=self.staff).json()
   self.assertEqual(all_data['totals']['checkouts'],3)
   self.assertEqual(all_data['overdue'][0]['count'],2)

 def test_analytics_empty_and_invalid_parameters(self):
  response=self.client.get('/admin/analytics?days=1',headers=self.staff)
  self.assertEqual(response.status_code,200,response.text);data=response.json()
  self.assertEqual(data['totals'],{'checkouts':0,'returns':0,'unique_borrowers':0})
  self.assertEqual(len(data['daily']),1);self.assertEqual(data['categories'],[])
  self.assertEqual([row['count'] for row in data['overdue']],[0,0,0])
  for query in ['days=0','days=367','days=oops','library_id=0']:
   self.assertEqual(self.client.get('/admin/analytics?'+query,headers=self.staff).status_code,422)
  self.assertEqual(self.client.get('/admin/analytics?library_id=999',headers=self.staff).status_code,404)

 def test_dashboard_aggregates_without_row_multiplication_or_per_book_queries(self):
  with self.factory() as db:
   db.add_all([BorrowRecord(user_id=2,book_id=1,due_date=datetime.now()+timedelta(days=1),status='borrowed'),
               BorrowRecord(user_id=3,book_id=1,due_date=datetime.now(),status='returned',returned_at=datetime.now())])
   db.add_all([Review(user_id=2,book_id=1,rating=4),Review(user_id=3,book_id=1,rating=2)])
   db.add(Reservation(user_id=2,book_id=1,status='pending'));db.commit()
  queries=[]
  def record(*args): queries.append(args[2])
  event.listen(self.engine,'before_cursor_execute',record)
  try:
   response=self.client.get('/admin/dashboard',headers=self.staff)
   baseline=len(queries)
   item=next(b for b in response.json()['popular_books'] if b['id']==1)
   self.assertEqual(item['borrow_count'],2);self.assertEqual(item['active_borrows'],1)
   self.assertEqual(item['review_count'],2);self.assertEqual(item['average_rating'],3)
   self.assertEqual(item['pending_reservations'],1)
   with self.factory() as db:
    db.add_all([Book(title=f'Extra {i}',author='Author') for i in range(30)]);db.commit()
   queries.clear()
   self.assertEqual(self.client.get('/admin/dashboard',headers=self.staff).status_code,200)
   self.assertEqual(len(queries),baseline)
  finally: event.remove(self.engine,'before_cursor_execute',record)

if __name__=='__main__':unittest.main()
