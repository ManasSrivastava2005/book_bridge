import unittest
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.models.library import Library
from app.models.user import User, UserRole
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.routers import books, admin
from app.services.auth import create_access_token

class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
  Base.metadata.create_all(self.engine);self.factory=sessionmaker(bind=self.engine)
  with self.factory() as db:
   db.add(Library(name='Library',code='TEST',campus='Test'))
   db.add(User(name='Staff',email='staff@example.com',hashed_password='unused',role=UserRole.LIBRARIAN))
   db.add(User(name='Student',email='student@example.com',hashed_password='unused',role=UserRole.STUDENT))
   db.add(Book(title='Original',author='Author',total_copies=3,available_copies=1));db.commit()
  def dep():
   with self.factory() as db:yield db
  app=FastAPI();app.include_router(books.router);app.include_router(admin.router);app.dependency_overrides[get_db]=dep
  self.client=TestClient(app);self.staff={'Authorization':'Bearer '+create_access_token(1,'librarian')};self.student={'Authorization':'Bearer '+create_access_token(2,'student')}
  self.addCleanup(self.client.close);self.addCleanup(self.engine.dispose)
 def test_metadata_persists_and_null_or_unsafe_fields_rejected(self):
  data={'title':'Updated','cover_image':'https://example.com/cover.jpg','publication_year':2026,'library_id':1}
  r=self.client.put('/books/1',headers=self.staff,json=data);self.assertEqual(r.status_code,200)
  for k,v in data.items():self.assertEqual(r.json()[k],v)
  for payload in [{'title':None},{'available_copies':None},{'title':'   '},{'cover_image':'javascript:alert(1)'},{'library_id':999}]:
   self.assertEqual(self.client.put('/books/1',headers=self.staff,json=payload).status_code,422)
 def test_stock_obligations_and_history_deletion(self):
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,status='borrowed',due_date=datetime.now()+timedelta(days=5)))
   db.add(Reservation(user_id=2,book_id=1,status='ready'));db.commit()
  self.assertEqual(self.client.put('/books/1',headers=self.staff,json={'available_copies':2}).status_code,409)
  r=self.client.put('/books/1',headers=self.staff,json={'total_copies':4})
  self.assertEqual(r.status_code,200);self.assertEqual(r.json()['available_copies'],2)
  self.assertEqual(self.client.delete('/books/1',headers=self.staff).status_code,409)
  with self.factory() as db:
   db.query(Reservation).delete();db.query(BorrowRecord).update({'status':'returned'});db.commit()
  self.assertEqual(self.client.delete('/books/1',headers=self.staff).status_code,409)
 def test_delete_unreferenced_and_student_denied(self):
  self.assertEqual(self.client.delete('/books/1',headers=self.student).status_code,403)
  self.assertEqual(self.client.delete('/books/1',headers=self.staff).status_code,204)
 def test_server_pagination_and_filters(self):
  with self.factory() as db:
   for i in range(24):db.add(Book(title=f'Filter {i}',author='Writer',category='CS',library_id=1,total_copies=1,available_copies=1))
   db.commit()
  r=self.client.get('/admin/catalog?search=Filter&category=CS&library_id=1&page=2',headers=self.staff)
  self.assertEqual(r.status_code,200);self.assertEqual(r.json()['total'],24);self.assertEqual(len(r.json()['items']),4)
  self.assertEqual(self.client.get('/admin/catalog',headers=self.student).status_code,403)

if __name__=='__main__':unittest.main()
