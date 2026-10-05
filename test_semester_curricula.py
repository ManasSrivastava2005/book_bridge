from test_personal_curriculum import PersonalCurriculumTests
from app.models.topic_progress import TopicProgress
from app.models.curriculum import Curriculum

class SemesterTests(PersonalCurriculumTests):
 def test_two_semesters_preserve_nodes_progress_and_owner_scope(self):
  first=self.save({**self.tree,'semester':3}).json();tid=first['subjects'][0]['children'][0]['children'][0]['id']
  self.assertEqual(self.academic_client.put(f'/academic/topics/{tid}/completion?completed=true',headers=self.student).status_code,200)
  second=self.save({**self.tree,'title':'Fourth semester','semester':4}).json()
  self.assertNotEqual(first['curriculum_id'],second['curriculum_id'])
  restored=self.academic_client.get('/academic/personal-curriculum?semester=3',headers=self.student).json()
  self.assertEqual(restored,first)
  self.assertEqual(self.academic_client.post('/academic/personal-curriculum/semesters/3/activate',headers=self.student).status_code,200)
  data=self.academic_client.get('/academic/curriculum',headers=self.student).json()
  self.assertTrue(data['subjects'][0]['units'][0]['topics'][0]['completed'])
  self.assertEqual(self.academic_client.post('/academic/personal-curriculum/semesters/3/activate',headers=self.waiting).status_code,404)
  self.assertEqual(self.academic_client.post('/academic/personal-curriculum/semesters/3/activate',headers=self.staff).status_code,403)
  with self.factory() as db:
   self.assertIsNotNone(db.get(TopicProgress,(2,tid)))
   self.assertEqual(db.query(Curriculum).filter_by(owner_user_id=2).count(),2)
