from test_catalog_management import CatalogTests
from app.models.quiz import Quiz,QuizQuestion
from app.models.quiz_attempt import QuizAttempt
from app.models.contribution import XPTransaction
from app.routers import student_quizzes
class StudentQuizTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(student_quizzes.router)
  with self.factory() as db:
   q=Quiz(title='Persisted quiz',book_id=1,chapter='Chapter 1',created_by=1,status='published',active=True,permission_confirmed=True);db.add(q);db.flush();self.qid=q.id
   for i in range(10):db.add(QuizQuestion(quiz_id=q.id,position=i,prompt=f'Question {i}',options=['Correct','Other'],correct_index=0,explanation='Explanation'))
   db.commit()
 def test_snapshot_scoring_daily_cap_retry_and_answer_secrecy(self):
  start=self.client.post(f'/student/quizzes/{self.qid}/start',headers=self.student)
  self.assertEqual(start.status_code,200,start.text);attempt=start.json();aid=attempt['attempt_id']
  self.assertNotIn('review',attempt);self.assertNotIn('correct_index',str(attempt['questions']))
  self.assertEqual(self.client.post(f'/student/quizzes/{self.qid}/start',headers=self.student).json()['attempt_id'],aid)
  with self.factory() as db:db.query(QuizQuestion).update({'correct_index':1});db.commit()
  url=f'/student/quizzes/attempts/{aid}/submit'
  self.assertEqual(self.client.post(url,headers=self.student,json={'answers':[0]*9}).status_code,422)
  self.assertEqual(self.client.post(url,headers=self.student,json={'answers':[9]*10}).status_code,422)
  for _ in range(2):self.assertEqual(self.client.post(url,headers=self.student,json={'answers':[0]*10}).json()['score'],100)
  self.assertEqual(self.client.post(url,headers=self.student,json={'answers':[1]*10}).status_code,409)
  second=self.client.post(f'/student/quizzes/{self.qid}/start',headers=self.student).json()['attempt_id']
  self.assertEqual(self.client.post(f'/student/quizzes/attempts/{second}/submit',headers=self.student,json={'answers':[1]*10}).json()['score'],100)
  with self.factory() as db:self.assertEqual(db.query(XPTransaction).filter_by(event_type='QUIZ').count(),1);self.assertEqual(db.query(QuizAttempt).count(),2)
  self.assertEqual(self.client.get('/student/quizzes').status_code,401)
  self.assertEqual(self.client.get('/student/quizzes',headers=self.staff).status_code,403)
 def test_draft_or_inactive_not_available(self):
  with self.factory() as db:db.get(Quiz,self.qid).active=False;db.commit()
  self.assertEqual(self.client.get('/student/quizzes',headers=self.student).json(),[])
  self.assertEqual(self.client.post(f'/student/quizzes/{self.qid}/start',headers=self.student).status_code,404)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
