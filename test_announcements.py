from test_catalog_management import CatalogTests
from app.routers import announcements,staff_users,auth,users
from app.models.announcement import AnnouncementDelivery
from app.models.notification import Notification
from app.models.curriculum import Curriculum,CurriculumNode,SubjectEnrollment
from app.models.user import User

class AnnouncementTests(CatalogTests):
 def setUp(self):
  super().setUp()
  for r in (announcements.router,staff_users.router,auth.router,users.router):self.client.app.include_router(r)
  with self.factory() as db:
   student=db.get(User,2);student.branch='CSE';student.semester=5
   c=Curriculum(title='Test',college='University',program='Degree',branch='CSE',semester=5,family='test',version=1);db.add(c);db.flush()
   s=CurriculumNode(curriculum_id=c.id,kind='subject',title='OS');db.add(s);db.flush();self.subject=s.id
   db.add(SubjectEnrollment(user_id=2,subject_id=s.id));db.commit()
 def payload(self,kind='all',value=None):return {'title':'Notice','message':'Fixture notice','target_kind':kind,'target_value':value}
 def test_targets_preview_and_idempotent_send(self):
  for kind,value in [('all',None),('branch','CSE'),('semester','5'),('subject',str(self.subject)),('individual','2')]:
   p=self.payload(kind,value)
   self.assertEqual(self.client.post('/admin/announcements/preview',headers=self.staff,json=p).json()['recipients'],1)
   r=self.client.post('/admin/announcements',headers=self.staff,json=p);self.assertEqual(r.status_code,201);id=r.json()['id']
   for _ in range(2):self.assertEqual(self.client.post(f'/admin/announcements/{id}/send',headers=self.staff).json()['sent'],1)
  with self.factory() as db:
   self.assertEqual(db.query(Notification).count(),5);self.assertEqual(db.query(AnnouncementDelivery).count(),5)
 def test_zero_target_roles_and_invalid_target(self):
  self.assertEqual(self.client.post('/admin/announcements',headers=self.student,json=self.payload()).status_code,403)
  self.assertEqual(self.client.get('/admin/announcements/audiences',headers=self.student).status_code,403)
  self.assertEqual(self.client.post('/admin/announcements',headers=self.staff,json=self.payload('individual','1')).status_code,422)
  r=self.client.post('/admin/announcements',headers=self.staff,json=self.payload('branch','Missing'))
  self.assertEqual(self.client.post(f'/admin/announcements/{r.json()["id"]}/send',headers=self.staff).status_code,409)
 def test_membership_is_staff_managed_on_both_profile_routes(self):
  for path in ('/auth/profile','/users/me'):
   self.assertEqual(self.client.put(path,headers=self.student,json={'library_id':1}).status_code,403)
   self.assertEqual(self.client.put(path,headers=self.student,json={'name':'Student Updated'}).status_code,200)
  self.assertEqual(self.client.put('/admin/users/2/membership',headers=self.student,json={'library_id':1}).status_code,403)
  self.assertEqual(self.client.put('/admin/users/2/membership',headers=self.staff,json={'library_id':1}).status_code,200)
  self.assertEqual(self.client.get('/auth/me',headers=self.student).json()['library_id'],1)
  self.assertEqual(self.client.put('/admin/users/2/membership',headers=self.staff,json={'library_id':999}).status_code,422)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
