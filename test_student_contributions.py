import json,uuid
from test_contribution_moderation import ContributionTests
from app.routers import student_contributions
from app.models.contribution import Contribution,XPTransaction
from app.models.user import User,UserRole
from app.services.auth import create_access_token
from app.services import contributions as storage
class StudentContributionTests(ContributionTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(student_contributions.router)
 def test_upload_retry_private_owner_status_and_approval_reward(self):
  data={'metadata':json.dumps({'title':'OS notes','subject':'OS','kind':'note'}),'request_key':str(uuid.uuid4())}
  def upload(content=b'Academic content.'):
   return self.client.post('/student/contributions',headers=self.student,data=data,files={'file':('notes.txt',content,'text/plain')})
  r=upload();self.assertEqual(r.status_code,201,r.text);cid=r.json()['id'];self.assertEqual(r.json()['status'],'PENDING')
  self.assertEqual(upload().json()['id'],cid);self.assertEqual(upload(b'Changed content.').status_code,409)
  with self.factory() as db:
   self.assertEqual(db.query(Contribution).count(),1);self.assertEqual(db.query(XPTransaction).count(),0)
   other=User(name='Other',email='other@example.com',hashed_password='unused',role=UserRole.STUDENT);db.add(other);db.commit();other_token={'Authorization':'Bearer '+create_access_token(other.id,'student')}
  self.assertEqual(len(list(storage.PRIVATE_DIR.iterdir())),1)
  self.assertEqual(self.client.get(f'/student/contributions/{cid}/file',headers=self.student).content,b'Academic content.')
  self.assertEqual(self.client.get(f'/student/contributions/{cid}/file',headers=other_token).status_code,404)
  self.assertEqual(self.client.get('/student/contributions',headers=other_token).json()['items'],[])
  self.assertEqual(self.client.get('/student/contributions').status_code,401)
  self.assertEqual(self.client.post(f'/admin/contributions/{cid}/decision',headers=self.staff,json={'decision':'APPROVED'}).status_code,200)
  self.assertEqual(self.client.get('/student/contributions',headers=self.student).json()['items'][0]['status'],'APPROVED')
  with self.factory() as db:self.assertEqual(sum(r.amount for r in db.query(XPTransaction)),2)

 def test_sections_preserve_owner_scope_and_all_history(self):
  ids={kind:self.pending(kind)[0] for kind in ('note','study_material','question_paper','question_bank')}
  self.pending('note',owner=1)
  for section,kinds in [('notes',('note','study_material')),('questions',('question_paper','question_bank'))]:
   result=self.client.get('/student/contributions',params={'section':section},headers=self.student)
   self.assertEqual(result.status_code,200,result.text)
   self.assertEqual({r['id'] for r in result.json()['items']},{ids[k] for k in kinds})
   self.assertEqual(result.json()['total'],2)
  self.assertEqual(self.client.get('/student/contributions',headers=self.student).json()['total'],4)
  self.assertEqual(self.client.get('/student/contributions?section=invalid',headers=self.student).status_code,422)
  self.assertEqual(self.client.get('/student/contributions?section=notes',headers=self.staff).status_code,403)
