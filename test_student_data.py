from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.database import get_db
from app.routers import student_data, staff_users
from app.models.user import User,UserRole
from app.models.academic_profile import AcademicProfile
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.library import Library
from test_staff_operations import StaffTests

class StudentDataTests(StaffTests):
 def setUp(self):
  super().setUp()
  app=FastAPI();app.include_router(student_data.router);app.include_router(staff_users.router)
  def dependency():
   with self.factory() as db:yield db
  app.dependency_overrides[get_db]=dependency
  self.directory_client=TestClient(app);self.addCleanup(self.directory_client.close)

 def test_filters_pagination_and_permission(self):
  with self.factory() as db:
   db.add(Library(name='Main',code='MAIN',campus='Campus'));db.flush()
   user=db.get(User,2);user.student_id='CSE42';user.branch='CS';user.semester=3;user.library_id=1
   db.add_all([User(name=f'Student {i}',email=f'fixture{i}@example.com',hashed_password='secret',role=UserRole.STUDENT) for i in range(21)]);db.commit()
  for path in ['/admin/student-data','/admin/student-data/2']:
   self.assertEqual(self.directory_client.get(path).status_code,401)
   self.assertEqual(self.directory_client.get(path,headers=self.student).status_code,403)
  r=self.directory_client.get('/admin/student-data?search=cse42&branch=CS&semester=3&library_id=1',headers=self.staff)
  self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['total'],1)
  self.assertEqual(r.json()['items'][0]['id'],2);self.assertNotIn('hashed_password',r.text)
  self.assertEqual(self.directory_client.get('/admin/student-data?library_id=0',headers=self.staff).json()['total'],22)
  self.assertEqual(len(self.directory_client.get('/admin/student-data?page=2',headers=self.staff).json()['items']),3)
  self.assertEqual(self.directory_client.get('/admin/student-data/1',headers=self.staff).status_code,404)

 def test_detail_allowlist_history_and_membership(self):
  with self.factory() as db:
   db.add(AcademicProfile(user_id=2,college='College',program='BTech',custom_subjects=['Operating Systems'],goals='PRIVATE GOAL'))
   db.add(BorrowRecord(user_id=2,book_id=1,status='borrowed',due_date=datetime.now()-timedelta(days=2)))
   db.add(Reservation(user_id=2,book_id=1,status='cancelled'));db.commit()
  response=self.directory_client.get('/admin/student-data/2',headers=self.staff)
  self.assertEqual(response.status_code,200,response.text);body=response.json()
  self.assertEqual(body['academic']['subjects'][0]['title'],'Operating Systems')
  self.assertEqual(body['overdue_ids'],[body['loans'][0]['id']])
  self.assertEqual(body['reservations'][0]['status'],'cancelled')
  for secret in ['hashed_password','PRIVATE GOAL','private_uploads','syllabus']:self.assertNotIn(secret,response.text)
  self.assertEqual(self.directory_client.put('/admin/users/2/membership',headers=self.student,json={'library_id':None}).status_code,403)
  self.assertEqual(self.directory_client.put('/admin/users/2/membership',headers=self.staff,json={'library_id':999}).status_code,422)
