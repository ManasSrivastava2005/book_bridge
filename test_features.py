"""Reviews and reservations regressions against disposable fixtures."""
import unittest
from test_catalog_management import CatalogTests
from app.routers import reviews, reservations
from app.models.book import Book
from app.models.borrow import BorrowRecord
from datetime import datetime

class FeatureTests(CatalogTests):
 def setUp(self):
  super().setUp()
  self.client.app.include_router(reviews.router)
  self.client.app.include_router(reservations.router)
 def test_review_upsert_rating_and_ownership(self):
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,status='returned',due_date=datetime.now()));db.commit()
  result=self.client.post('/reviews/',headers=self.student,json={'book_id':1,'rating':5,'comment':'Useful'})
  self.assertEqual(result.status_code,201,result.text);rid=result.json()['id']
  updated=self.client.post('/reviews/',headers=self.student,json={'book_id':1,'rating':3})
  self.assertEqual(updated.json()['id'],rid)
  self.assertEqual(len(self.client.get('/reviews/book/1').json()),1)
  rating=self.client.get('/reviews/book/1/rating').json()
  self.assertEqual(rating['average_rating'],3);self.assertEqual(rating['total_reviews'],1)
  self.assertEqual(self.client.post('/reviews/',headers=self.student,json={'book_id':1,'rating':6}).status_code,422)
  self.assertEqual(self.client.post('/reviews/',json={'book_id':1,'rating':5}).status_code,401)
  self.assertEqual(self.client.delete(f'/reviews/{rid}',headers=self.student).status_code,204)
 def test_reservation_availability_duplicate_and_visibility(self):
  self.assertEqual(self.client.post('/reservations/',headers=self.student,json={'book_id':1}).status_code,400)
  self.assertEqual(self.client.post('/reservations/',headers=self.student,json={'book_id':999}).status_code,404)
  with self.factory() as db:
   db.get(Book,1).available_copies=0;db.commit()
  created=self.client.post('/reservations/',headers=self.student,json={'book_id':1})
  self.assertEqual(created.status_code,201,created.text)
  self.assertEqual(self.client.post('/reservations/',headers=self.student,json={'book_id':1}).status_code,400)
  self.assertEqual(len(self.client.get('/reservations/my',headers=self.student).json()),1)
  self.assertEqual(self.client.get('/reservations/my',headers=self.staff).json(),[])
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None

if __name__=='__main__':unittest.main()
