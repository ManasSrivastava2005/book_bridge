from test_student_badges import BadgeTests
from app.models.badge import UserBadge
from app.models.borrow import BorrowRecord
from app.models.review import Review
from app.models.contribution import XPTransaction
from datetime import datetime
class AchievementTests(BadgeTests):
 def test_real_progress_unknown_legacy_and_zero_reward(self):
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,status='returned',due_date=datetime(2026,12,1)))
   db.add(Review(user_id=2,book_id=1,rating=5,comment='Verified reading'))
   from app.models.badge import Badge
   if not db.query(Badge).filter_by(name='AI Learner').first():db.add(Badge(name='AI Learner',description='Ask 10 questions',icon='bot',xp_reward=100))
   db.commit()
  result=self.client.get('/badges/achievements',headers=self.student)
  self.assertEqual(result.status_code,200,result.text);items={b['name']:b for b in result.json()['badges']}
  self.assertEqual(items['Book Explorer']['current'],1)
  self.assertEqual(items['Reviewer']['current'],1)
  self.assertTrue(items['First Borrow']['earned'])
  self.assertIsNone(items['AI Learner']['current'])
  self.assertTrue(all(b['unlock_xp']==0 for b in items.values()))
  self.client.get('/badges/achievements',headers=self.student)
  with self.factory() as db:self.assertEqual(db.query(XPTransaction).count(),0)
