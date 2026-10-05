from datetime import datetime
from unittest.mock import patch
from test_catalog_management import CatalogTests
from app.models.user import User,UserRole
from app.models.contribution import XPTransaction
from app.routers import leaderboard

class LeaderboardTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(leaderboard.router)
  with self.factory() as db:
   db.get(User,2).branch='CS';db.get(User,2).semester=1
   db.add(User(name='Other',email='private@example.com',hashed_password='unused',role=UserRole.STUDENT,branch='IT',semester=2));db.flush()
   db.add(XPTransaction(user_id=2,amount=25,event_key='week',created_at=datetime(2026,9,23)))
   db.add(XPTransaction(user_id=3,amount=100,event_key='month',created_at=datetime(2026,9,2)))
   db.add(XPTransaction(user_id=2,amount=1000,event_key='old',created_at=datetime(2026,8,2)))
   db.add(XPTransaction(user_id=1,amount=99999,event_key='staff'));db.commit()
  p=patch.object(leaderboard,'now_utc',return_value=datetime(2026,9,26));p.start();self.addCleanup(p.stop)
 def test_periods_filters_and_private_fields(self):
  for period,first in [('weekly','Student'),('monthly','Other'),('all_time','Student')]:
   result=self.client.get('/leaderboard',params={'period':period},headers=self.student)
   self.assertEqual(result.status_code,200,result.text);data=result.json()
   self.assertEqual(data['items'][0]['name'],first);self.assertEqual(data['total'],2)
   for row in data['items']:
    self.assertEqual(set(row),{'rank','name','avatar','xp','level','reading_streak','pages_read','is_current'})
  self.assertEqual(self.client.get('/leaderboard?scope=branch',headers=self.student).json()['total'],1)
  self.assertEqual(self.client.get('/leaderboard?scope=semester',headers=self.student).json()['total'],1)
  self.assertEqual(self.client.get('/leaderboard').status_code,401)
  self.assertEqual(self.client.get('/leaderboard?period=bad',headers=self.student).status_code,422)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
