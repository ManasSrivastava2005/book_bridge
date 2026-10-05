from test_academic_profile import AcademicTests
from app.models.curriculum import Curriculum,CurriculumNode,SubjectEnrollment
from app.models.topic_progress import TopicProgress
class TopicTests(AcademicTests):
 def test_selection_progress_idempotency_and_ownership(self):
  with self.factory() as db:
   c=Curriculum(family='progress',title='OS',college='Uni',program='CS',branch='CS',semester=1);db.add(c);db.flush()
   s=CurriculumNode(curriculum_id=c.id,kind='subject',title='OS');db.add(s);db.flush()
   u=CurriculumNode(curriculum_id=c.id,parent_id=s.id,kind='unit',title='Memory');db.add(u);db.flush()
   t=CurriculumNode(curriculum_id=c.id,parent_id=u.id,kind='topic',title='Paging');db.add(t);db.commit();cid=c.id;sid=s.id;tid=t.id
  self.assertEqual(self.client.put('/academic/profile',headers=self.student,json={'curriculum_id':cid,'subject_ids':[sid]}).status_code,200)
  path=self.client.get('/academic/learning-path',headers=self.student).json()
  self.assertEqual(path['steps'][0]['status'],'next');self.assertEqual(path['steps'][0]['title'],'Paging')
  self.assertEqual(self.client.get('/academic/learning-path',headers=self.staff).status_code,403)
  for _ in range(2):
   r=self.client.put(f'/academic/topics/{tid}/completion?completed=true',headers=self.student)
   self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['subjects'][0]['progress_percent'],100)
  self.assertEqual(self.client.get('/academic/learning-path',headers=self.student).json()['steps'][0]['status'],'completed')
  with self.factory() as db:self.assertEqual(db.query(TopicProgress).count(),1);self.assertEqual(db.query(SubjectEnrollment).count(),1)
  self.assertEqual(self.client.put(f'/academic/topics/{tid}/completion?completed=true',headers=self.staff).status_code,403)
  self.assertEqual(self.client.get('/academic/curriculum',headers=self.staff).status_code,403)
  r=self.client.put(f'/academic/topics/{tid}/completion?completed=false',headers=self.student)
  self.assertEqual(r.json()['subjects'][0]['progress_percent'],0)
 test_old_accounts_and_optional_signup=None
 test_profile_validation_and_owner_scope=None
