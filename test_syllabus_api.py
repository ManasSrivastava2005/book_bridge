import tempfile
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.database import get_db
from app.routers import syllabus,personal_curriculum
from app.models.syllabus_upload import SyllabusUpload
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.academic_profile import AcademicProfile
from test_staff_operations import StaffTests
from test_syllabus_processing import text_pdf

class SyllabusAPITests(StaffTests):
 def setUp(self):
  super().setUp();temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.folder=Path(temporary.name)
  patched=patch.object(syllabus,'PRIVATE_SYLLABUS_DIR',self.folder);patched.start();self.addCleanup(patched.stop)
  app=FastAPI();app.include_router(syllabus.router);app.include_router(personal_curriculum.router)
  def dependency():
   with self.factory() as db:yield db
  app.dependency_overrides[get_db]=dependency;self.syllabus_client=TestClient(app);self.addCleanup(self.syllabus_client.close)
  self.pdf=text_pdf(['Course: Operating Systems','Unit 1: Memory','Topic: Paging'])
 def upload(self,key=None,headers=None,contents=None):
  return self.syllabus_client.post('/academic/syllabi',headers=headers or self.student,data={'request_id':key or str(uuid4())},files={'file':('syllabus.pdf',contents or self.pdf,'application/pdf')})
 def test_private_upload_no_curriculum_change_and_idempotent_confirmation(self):
  key=str(uuid4());r=self.upload(key);self.assertEqual(r.status_code,201,r.text);row=r.json();rid=row['id']
  self.assertEqual(self.upload(key).json()['id'],rid)
  self.assertEqual(self.upload(key,contents=text_pdf(['Different text'])).status_code,409)
  with self.factory() as db:self.assertIsNone(db.get(AcademicProfile,2));self.assertEqual(db.query(Curriculum).count(),0)
  self.assertEqual(self.syllabus_client.get(f'/academic/syllabi/{rid}/file',headers=self.student).content,self.pdf)
  for headers in [self.waiting,self.staff]:
   expected=403 if headers==self.staff else 404
   for suffix in ['', '/file']:self.assertEqual(self.syllabus_client.get(f'/academic/syllabi/{rid}'+suffix,headers=headers).status_code,expected)
  self.assertEqual(self.syllabus_client.get('/academic/syllabi',headers=self.waiting).json(),[])
  payload={'title':'Corrected OS','subjects':row['proposal']['subjects']}
  payload['subjects'][0]['children'][0]['children'][0]['title']='Virtual memory'
  for _ in range(2):self.assertEqual(self.syllabus_client.post(f'/academic/syllabi/{rid}/confirm',headers=self.student,json=payload).status_code,200)
  self.assertEqual(self.syllabus_client.post(f'/academic/syllabi/{rid}/confirm',headers=self.student,json={**payload,'title':'Different'}).status_code,409)
  with self.factory() as db:
   self.assertEqual(db.query(Curriculum).count(),1);self.assertEqual(db.query(CurriculumNode).count(),3)
   self.assertEqual(db.get(SyllabusUpload,rid).state,'confirmed')
 def test_staff_upload_denied_and_invalid_pdf_leaves_no_file(self):
  self.assertEqual(self.upload(headers=self.staff).status_code,403)
  self.assertEqual(self.upload(contents=b'%PDF-invalid').status_code,400)
  self.assertEqual(list(self.folder.iterdir()),[])
