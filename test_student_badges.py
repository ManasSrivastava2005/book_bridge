from datetime import datetime
from test_catalog_management import CatalogTests
from app.services.badges import seed_badges,award_badges
from app.models.badge import Badge,UserBadge
from app.models.borrow import BorrowRecord
from app.models.contribution import XPTransaction
from app.routers import badges

class BadgeTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(badges.router)
  with self.factory() as db:seed_badges(db);db.commit()
 def test_earned_requires_ownership_and_awards_are_idempotent(self):
  data=self.client.get('/badges/my',headers=self.student).json()
  self.assertTrue(all(not badge['earned'] for badge in data))
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,status='borrowed',due_date=datetime(2026,12,1)))
   db.add(XPTransaction(user_id=2,amount=2000,event_key='fixture'));db.commit()
   award_badges(db,2);award_badges(db,2);db.commit()
   self.assertEqual(db.query(UserBadge).count(),2)
   self.assertEqual(db.query(XPTransaction).count(),1)
  earned={b['name'] for b in self.client.get('/badges/my',headers=self.student).json() if b['earned']}
  self.assertEqual(earned,{'First Borrow','Bronze Reader'})
  self.assertTrue(all(not b['earned'] for b in self.client.get('/badges/my',headers=self.staff).json()))
  self.assertEqual(self.client.get('/badges/my').status_code,401)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
