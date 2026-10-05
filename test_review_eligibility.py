from datetime import datetime
from test_features import FeatureTests
from app.models.borrow import BorrowRecord
from app.models.review import Review

class EligibilityTests(FeatureTests):
 def test_unverified_legacy_review_preserved_but_not_editable(self):
  with self.factory() as db:
   db.add(Review(user_id=2,book_id=1,rating=3,comment='Legacy'));db.commit()
  self.assertFalse(self.client.get('/reviews/book/1/eligibility',headers=self.student).json()['eligible'])
  self.assertEqual(self.client.post('/reviews/',headers=self.student,json={'book_id':1,'rating':5}).status_code,403)
  self.assertEqual(self.client.get('/reviews/book/1').json()[0]['comment'],'Legacy')
  self.assertEqual(self.client.post('/reviews/',headers=self.staff,json={'book_id':1,'rating':5}).status_code,403)
  self.assertEqual(self.client.get('/reviews/book/1/eligibility').status_code,401)

 def test_active_and_returned_loans_qualify_only_for_owned_book(self):
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,status='borrowed',due_date=datetime.now()));db.commit()
  self.assertTrue(self.client.get('/reviews/book/1/eligibility',headers=self.student).json()['eligible'])
  self.assertEqual(self.client.post('/reviews/',headers=self.student,json={'book_id':1,'rating':5}).status_code,201)
  with self.factory() as db:db.query(BorrowRecord).update({'status':'returned'});db.commit()
  self.assertTrue(self.client.get('/reviews/book/1/eligibility',headers=self.student).json()['eligible'])
  response=self.client.post('/reviews/',headers=self.student,json={'book_id':1,'rating':4})
  self.assertEqual(response.status_code,201)
  self.assertEqual(len(self.client.get('/reviews/book/1').json()),1)
