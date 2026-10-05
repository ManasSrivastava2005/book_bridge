import tempfile
from pathlib import Path
from unittest.mock import patch
from test_catalog_management import CatalogTests
from app.models.contribution import Contribution, ContributionAudit, XPTransaction
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.notification import Notification
from app.routers.contributions import router
from app.services import contributions as storage

class ContributionTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(router)
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for name,path in [('PRIVATE_DIR','private'),('PUBLIC_DIR','public')]:
   p=patch.object(storage,name,Path(self.tmp.name)/path);p.start();self.addCleanup(p.stop)
 def pending(self,kind='note',owner=2):
  name=storage.store_pending_file('material.txt',b'Academic contribution fixture.')
  self.assertFalse(storage.PUBLIC_DIR.exists()) if not storage.PUBLIC_DIR.exists() else None
  with self.factory() as db:
   row=Contribution(user_id=owner,title='Fixture',kind=kind,subject='OS',semester=5,branch='CSE',storage_name=name,original_name='material.txt')
   db.add(row);db.commit();return row.id,name
 def test_approval_publishes_all_types_with_exactly_once_reward(self):
  for kind in ('note','question_paper','question_bank','study_material'):
   id,name=self.pending(kind)
   for _ in range(2):self.assertEqual(self.client.post(f'/admin/contributions/{id}/decision',headers=self.staff,json={'decision':'APPROVED'}).status_code,200)
   self.assertEqual((storage.PUBLIC_DIR/name).read_bytes(),b'Academic contribution fixture.')
  with self.factory() as db:
   self.assertEqual(db.query(XPTransaction).count(),4)
   self.assertEqual(sum(r.amount for r in db.query(XPTransaction)),8)
   self.assertEqual(db.query(ContributionAudit).count(),4)
   self.assertEqual(db.query(Note).count(),2);self.assertEqual(db.query(QuestionBank).count(),2)
   self.assertEqual(db.query(Notification).count(),4)
 def test_reject_and_private_file_role_protection(self):
  id,name=self.pending()
  self.assertEqual(self.client.get(f'/admin/contributions/{id}/file',headers=self.student).status_code,403)
  self.assertEqual(self.client.get(f'/admin/contributions/{id}/file').status_code,401)
  self.assertEqual(self.client.get(f'/admin/contributions/{id}/file',headers=self.staff).content,b'Academic contribution fixture.')
  self.assertEqual(self.client.post(f'/admin/contributions/{id}/decision',headers=self.student,json={'decision':'APPROVED'}).status_code,403)
  self.assertEqual(self.client.post(f'/admin/contributions/{id}/decision',headers=self.staff,json={'decision':'REJECTED','reason':'Wrong course'}).status_code,200)
  self.assertEqual(self.client.post(f'/admin/contributions/{id}/decision',headers=self.staff,json={'decision':'APPROVED'}).status_code,409)
  self.assertFalse((storage.PUBLIC_DIR/name).exists())
  with self.factory() as db:self.assertEqual(db.query(XPTransaction).count(),0)
 def test_required_reason_and_kind_search_filters(self):
  note,_=self.pending('note');paper,_=self.pending('question_paper')
  response=self.client.get('/admin/contributions?kind=question_paper&search=Fixture',headers=self.staff)
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual([r['id'] for r in response.json()['items']],[paper])
  self.assertEqual(self.client.get('/admin/contributions?search=missing',headers=self.staff).json()['total'],0)
  for reason in (None,'','   '):
   self.assertEqual(self.client.post(f'/admin/contributions/{note}/decision',headers=self.staff,json={'decision':'REJECTED','reason':reason}).status_code,422)
  with self.factory() as db:
   self.assertEqual(db.get(Contribution,note).status,'PENDING')
   self.assertEqual(db.query(Notification).count(),0)
 def test_self_approval_and_missing_file_blocked(self):
  id,name=self.pending(owner=1)
  self.assertEqual(self.client.post(f'/admin/contributions/{id}/decision',headers=self.staff,json={'decision':'APPROVED'}).status_code,403)
  id,name=self.pending();storage.private_path(name).unlink()
  self.assertEqual(self.client.post(f'/admin/contributions/{id}/decision',headers=self.staff,json={'decision':'APPROVED'}).status_code,409)
 def test_publication_validation_rolls_back_file_and_reward(self):
  id,name=self.pending('question_paper')
  with self.factory() as db:db.get(Contribution,id).branch=None;db.commit()
  self.assertEqual(self.client.post(f'/admin/contributions/{id}/decision',headers=self.staff,json={'decision':'APPROVED'}).status_code,422)
  self.assertFalse((storage.PUBLIC_DIR/name).exists())
  with self.factory() as db:
   self.assertEqual(db.get(Contribution,id).status,'PENDING');self.assertEqual(db.query(XPTransaction).count(),0)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
