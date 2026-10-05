from test_catalog_management import CatalogTests
from app.routers import academic,auth
from app.models.academic_profile import AcademicProfile
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.user import User
class AcademicTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(academic.router);self.client.app.include_router(auth.router)
 def test_old_accounts_and_optional_signup(self):
  result=self.client.get('/academic/profile',headers=self.student)
  self.assertEqual(result.status_code,200);self.assertIsNone(result.json()['curriculum_id'])
  payload={'name':'Optional','email':'optional@example.com','password':'test-only-password'}
  r=self.client.post('/auth/register',json=payload);self.assertEqual(r.status_code,201,r.text)
  self.assertIsNone(r.json()['branch']);self.assertIsNone(r.json()['semester'])
  with self.factory() as db:self.assertIsNone(db.get(AcademicProfile,r.json()['id']))
 def test_profile_validation_and_owner_scope(self):
  with self.factory() as db:
   c=Curriculum(family='fixture',title='CS',college='University',program='Degree',branch='CS',semester=1);db.add(c);db.flush()
   n=CurriculumNode(curriculum_id=c.id,kind='subject',title='OS');db.add(n);db.commit();cid=c.id;sid=n.id
  payload={'college':'University','program':'Degree','branch':'CS','semester':1,'curriculum_id':cid,'subject_ids':[sid],'custom_subjects':['Robotics'],'goals':'Learn'}
  r=self.client.put('/academic/profile',headers=self.student,json=payload);self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(self.client.get('/academic/profile',headers=self.student).json()['custom_subjects'],['Robotics'])
  self.assertEqual(self.client.get('/academic/profile',headers=self.staff).status_code,403)
  self.assertEqual(self.client.put('/academic/profile',headers=self.student,json={**payload,'subject_ids':[999]}).status_code,422)
  self.assertEqual(self.client.put('/academic/profile',headers=self.student,json={**payload,'library_id':1}).status_code,422)
  self.assertEqual(self.client.put('/academic/profile',headers=self.student,json={**payload,'semester':99}).status_code,422)
  self.assertEqual(self.client.get('/academic/profile').status_code,401)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
