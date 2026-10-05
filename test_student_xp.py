import unittest
from datetime import datetime, timezone, timedelta
from app.models.contribution import XPTransaction
from app.models.user import User, UserRole
from app.services.xp import award_login
from app.routers.xp import router
from app.services.auth import create_access_token
from test_staff_auth import StaffAuthTests

class XPTests(StaffAuthTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(router)
 def test_successful_login_only_and_daily_deduplication(self):
  payload={'email':'student@example.com','password':'isolated-test-password'}
  self.assertEqual(self.client.post('/auth/login',json={**payload,'password':'wrong'}).status_code,401)
  with self.factory() as db:self.assertEqual(db.query(XPTransaction).count(),0)
  for _ in range(3):self.assertEqual(self.client.post('/auth/login',json=payload).status_code,200)
  self.client.post('/auth/login',json={'email':'librarian@example.com','password':'isolated-test-password'})
  with self.factory() as db:
   rows=db.query(XPTransaction).all();self.assertEqual(len(rows),1);self.assertEqual(rows[0].amount,25);self.assertEqual(rows[0].event_type,'LOGIN')
 def test_calendar_boundary_and_rollback(self):
  with self.factory() as db:
   user=db.query(User).filter(User.role==UserRole.STUDENT).one()
   now=datetime(2026,1,1,23,59,tzinfo=timezone.utc)
   self.assertTrue(award_login(db,user,now));self.assertFalse(award_login(db,user,now))
   self.assertTrue(award_login(db,user,now+timedelta(minutes=1)));db.commit()
   self.assertEqual(db.query(XPTransaction).count(),2)
   self.assertTrue(award_login(db,user,now+timedelta(days=3)));db.rollback()
   self.assertEqual(db.query(XPTransaction).count(),2)
 def test_history_owner_scope_pagination_and_no_award_endpoint(self):
  with self.factory() as db:
   user=db.query(User).filter(User.role==UserRole.STUDENT).one();uid=user.id
   other=db.query(User).filter(User.role==UserRole.LIBRARIAN).one()
   db.add(XPTransaction(user_id=uid,amount=2,event_key='contribution:42:approved'))
   db.add(XPTransaction(user_id=other.id,amount=2,event_key='contribution:43:approved'));db.commit()
  headers={'Authorization':'Bearer '+create_access_token(uid,'student')}
  self.assertEqual(self.client.get('/xp/history').status_code,401)
  result=self.client.get('/xp/history?page_size=1',headers=headers).json()
  self.assertEqual(result['lifetime_xp'],2);self.assertEqual(result['total'],1)
  self.assertEqual(result['items'][0]['event_type'],'CONTRIBUTION')
  self.assertEqual(self.client.get('/xp/history?page=0',headers=headers).status_code,422)
  self.assertEqual(self.client.post('/xp/history',headers=headers,json={'amount':999999}).status_code,405)

if __name__=='__main__':unittest.main()
