from datetime import date
from test_catalog_management import CatalogTests
from app.models.contribution import XPTransaction
from app.services.missions import daily_missions

class MissionTests(CatalogTests):
 def test_only_persisted_current_day_owner_events_complete_missions(self):
  with self.factory() as db:
   db.add(XPTransaction(user_id=2,event_key='READING:2:2026-09-26',event_type='READING',amount=25))
   db.add(XPTransaction(user_id=2,event_key='QUIZ:2:2026-09-25',event_type='QUIZ',amount=25))
   db.add(XPTransaction(user_id=1,event_key='STREAK:1:2026-09-26',event_type='STREAK',amount=25));db.commit()
   missions=daily_missions(db,2,date(2026,9,26))
   self.assertEqual([m['completed'] for m in missions],[True,False,False,False])
   self.assertTrue(all(not m['completed'] for m in daily_missions(db,2,date(2026,9,27))))
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
