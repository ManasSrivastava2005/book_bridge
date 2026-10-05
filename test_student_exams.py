from test_academic_profile import AcademicTests
from app.routers import student_exams
from app.models.student_exam import StudentExam
class ExamTests(AcademicTests):
 def test_exam_crud_owner_scope_and_validation(self):
  self.client.app.include_router(student_exams.router)
  self.client.put('/academic/profile',headers=self.student,json={'custom_subjects':['Robotics']})
  payload={'custom_subject':'Robotics','name':'Midterm','exam_type':'Midterm','date':'2026-12-01'}
  r=self.client.post('/academic/exams',headers=self.student,json=payload);self.assertEqual(r.status_code,201,r.text);eid=r.json()['id']
  self.assertEqual(self.client.get('/academic/exams',headers=self.staff).status_code,403)
  self.assertEqual(self.client.put(f'/academic/exams/{eid}',headers=self.staff,json=payload).status_code,403)
  r=self.client.put(f'/academic/exams/{eid}',headers=self.student,json={**payload,'date':'2026-12-02'});self.assertEqual(r.json()['date'],'2026-12-02')
  self.assertEqual(self.client.post('/academic/exams',headers=self.student,json={**payload,'custom_subject':'Unknown'}).status_code,422)
  self.assertEqual(self.client.post('/academic/exams',headers=self.student,json={**payload,'exam_type':'Invalid'}).status_code,422)
  self.assertEqual(self.client.delete(f'/academic/exams/{eid}',headers=self.student).status_code,204)
  with self.factory() as db:self.assertEqual(db.query(StudentExam).count(),0)
 test_old_accounts_and_optional_signup=None
 test_profile_validation_and_owner_scope=None
