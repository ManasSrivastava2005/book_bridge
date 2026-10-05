import unittest
from app.services.xp import level_from_xp
from test_student_xp import XPTests
from app.models.user import User,UserRole
from app.models.contribution import XPTransaction
from app.services.auth import create_access_token

class FormulaTests(unittest.TestCase):
 def test_every_level_boundary(self):
  for level in range(1,51):
   start=100*(level-1)*level
   result=level_from_xp(start)
   self.assertEqual(result['level'],level)
   self.assertEqual(result['current_level_xp'],0)
   self.assertEqual(result['xp_required_this_level'],200*level)
   if start:self.assertEqual(level_from_xp(start-1)['level'],level-1)
 def test_cap_and_lifetime_preserved(self):
  result=level_from_xp(1000000)
  self.assertEqual(result['level'],50);self.assertEqual(result['lifetime_xp'],1000000)
  self.assertEqual(result['progress_percent'],100);self.assertEqual(result['xp_remaining'],0)
 def test_partial_progress(self):
  result=level_from_xp(300)
  self.assertEqual(result['level'],2);self.assertEqual(result['current_level_xp'],100)
  self.assertEqual(result['xp_remaining'],300);self.assertEqual(result['progress_percent'],25)

class LevelAPITests(XPTests):
 def test_level_from_ledger_only(self):
  with self.factory() as db:
   user=db.query(User).filter(User.role==UserRole.STUDENT).one();uid=user.id
   db.add(XPTransaction(user_id=uid,amount=600,event_key='fixture'));db.commit()
  headers={'Authorization':'Bearer '+create_access_token(uid,'student')}
  result=self.client.get('/xp/level',headers=headers)
  self.assertEqual(result.status_code,200);self.assertEqual(result.json()['level'],3)
  self.assertEqual(self.client.get('/xp/level').status_code,401)
  self.assertEqual(self.client.post('/xp/level',headers=headers,json={'level':50}).status_code,405)

if __name__=='__main__':unittest.main()
