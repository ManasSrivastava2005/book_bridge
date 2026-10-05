from datetime import datetime,timedelta
from test_catalog_management import CatalogTests
from app.models.borrow import BorrowRecord
from app.models.review import Review
from app.models.book import Book

class DiscoverTests(CatalogTests):
 def test_popularity_uses_history_without_join_multiplication(self):
  with self.factory() as db:
   db.get(Book,1).library_id=1
   db.add(Book(title='Never borrowed',author='Author',total_copies=1,available_copies=1))
   db.add_all([BorrowRecord(user_id=2,book_id=1,status=status,due_date=datetime.now()+timedelta(days=1)) for status in ['borrowed','returned']])
   db.add(Review(user_id=2,book_id=1,rating=4));db.commit()
  response=self.client.get('/books/discover');self.assertEqual(response.status_code,200,response.text)
  books={r['id']:r for r in response.json()}
  self.assertEqual(books[1]['borrow_count'],2);self.assertEqual(books[1]['review_count'],1)
  self.assertEqual(books[1]['average_rating'],4);self.assertEqual(books[1]['library_name'],'Library')
  self.assertEqual(books[2]['borrow_count'],0);self.assertIsNone(books[2]['average_rating'])
