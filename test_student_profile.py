import unittest
from datetime import date
from app.routers.dashboard import router
from app.models.quiz_attempt import QuizAttempt
from app.models.reading_session import ReadingDay
from app.models.user import User,UserRole
from app.services.auth import create_access_token
from test_staff_auth import StaffAuthTests
class StudentProgressTests(StaffAuthTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(router)
 def test_progress_is_owner_scoped_and_empty_is_real(self):
  with self.factory() as db:
   student=db.query(User).filter_by(role=UserRole.STUDENT).one()
   other=db.query(User).filter_by(role=UserRole.ADMIN).one()
   token=create_access_token(student.id,'student')
   db.add(ReadingDay(user_id=other.id,date=date.today(),duration_seconds=900,pages=['1:1']))
   db.commit()
  self.assertEqual(self.client.get('/dashboard/student-progress').status_code,401)
  data=self.client.get('/dashboard/student-progress',headers={'Authorization':'Bearer '+token}).json()
  self.assertEqual(data['reading_seconds'],0)
  self.assertEqual(data['books_read'],0)
  self.assertEqual(data['completed_quizzes'],0)
  self.assertIsNone(data['average_quiz_score'])
  self.assertEqual(data['approved_contributions'],0)
  self.assertEqual(data['subjects'],[])
if __name__=='__main__':unittest.main()
