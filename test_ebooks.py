"""Managed e-book storage tests, using temporary files and an isolated database."""
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pypdf import PdfWriter
from sqlalchemy.exc import SQLAlchemyError
from app.services import ebook_storage
from app.models.library import Library
from app.models.user import User
from app.models.digital_resource import DigitalResource
from test_staff_operations import StaffTests

class EbookTests(StaffTests):
 def setUp(self):
  super().setUp()
  temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup)
  self.directory=Path(temporary.name)
  patcher=patch.object(ebook_storage,'PRIVATE_EBOOK_DIR',self.directory);patcher.start();self.addCleanup(patcher.stop)
  writer=PdfWriter();writer.add_blank_page(width=300,height=400);stream=io.BytesIO();writer.write(stream);self.pdf=stream.getvalue()
  self.payload={'title':'Private PDF','author':'Author','library_id':None,'is_published':False,'access_type':'free','distribution_basis':'permission','license_name':'Fixture permission','rights_evidence':'Original acceptance fixture permitted for testing.'}
 def upload(self,headers=None,content=None,filename='book.pdf',payload=None):
  return self.client.post('/digital-resources/upload',headers=headers or self.staff,data={'metadata':json.dumps(payload or self.payload)},files={'file':(filename,self.pdf if content is None else content,'application/pdf')})
 def test_protected_draft_and_published_delivery(self):
  response=self.upload();self.assertEqual(response.status_code,201,response.text);resource=response.json();url=resource['file_url']
  self.assertEqual(self.client.get(url).status_code,401)
  self.assertEqual(self.client.get(url,headers=self.student).status_code,404)
  self.assertEqual(self.client.get(url,headers=self.staff).content,self.pdf)
  self.assertEqual(self.client.put('/admin/digital-resources/'+str(resource['id']),headers=self.staff,json={**resource,'is_published':True}).status_code,200)
  self.assertEqual(self.client.get(url,headers=self.student).content,self.pdf)
  self.assertEqual(self.client.get(url,headers=self.student).headers['cache-control'],'private, no-store')
  self.assertEqual(self.client.put('/admin/digital-resources/'+str(resource['id']),headers=self.staff,json={**resource,'is_published':True,'download_allowed':False}).status_code,200)
  self.assertEqual(self.client.get(url+'?download=true',headers=self.student).status_code,403)
  self.assertEqual(self.client.get(url,headers=self.student).status_code,200)
  self.assertEqual(self.client.delete('/digital-resources/'+str(resource['id']),headers=self.staff).status_code,204)
  self.assertEqual(list(self.directory.iterdir()),[])
 def test_membership_and_reference_reassignment(self):
  with self.factory() as db:
   lib=Library(name='Members',code='MEM',campus='Test');db.add(lib);db.flush();lid=lib.id;db.get(User,2).library_id=lid;db.commit()
  response=self.upload(payload={**self.payload,'library_id':lid,'access_type':'library_members','is_published':True})
  self.assertEqual(response.status_code,201,response.text);resource=response.json();url=resource['file_url']
  self.assertEqual(self.client.get(url,headers=self.student).status_code,200)
  self.assertEqual(self.client.get(url,headers=self.waiting).status_code,403)
  self.assertEqual(self.client.post('/digital-resources/',headers=self.staff,json=resource).status_code,422)
  self.assertEqual(self.client.put('/admin/digital-resources/'+str(resource['id']),headers=self.staff,json={**resource,'file_url':'/uploads/other.pdf'}).status_code,422)
 def test_validation_and_atomic_cleanup(self):
  self.assertEqual(self.upload(headers=self.student).status_code,403)
  for kwargs in [{'content':b''},{'content':b'not a PDF'},{'filename':'book.exe'},{'content':b'%PDF-broken'}]:
   self.assertEqual(self.upload(**kwargs).status_code,400)
  self.assertEqual(self.upload(payload={**self.payload,'access_type':'library_members'}).status_code,422)
  with patch.object(self.factory.class_,'commit',side_effect=SQLAlchemyError('test')):
   self.assertEqual(self.upload().status_code,500)
  self.assertEqual(list(self.directory.iterdir()),[])
  with self.factory() as db:self.assertEqual(db.query(DigitalResource).count(),0)
