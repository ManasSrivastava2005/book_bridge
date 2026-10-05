from app.services import badges  # Register reward tables before isolated schema creation.
from datetime import datetime,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch,Mock
from test_catalog_management import CatalogTests
from app.models.digital_resource import DigitalResource
from app.models.reading_session import ReadingSession,ReadingDay
from app.models.contribution import XPTransaction
from app.routers import reading_activity as reading
from app.services import ebook_storage

class ReadingTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(reading.router)
  folder=TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name)
  filename='a'*32+'.pdf';(root/filename).write_bytes(b'%PDF-fixture')
  for target,value in ((ebook_storage,'PRIVATE_EBOOK_DIR'),):
   p=patch.object(target,value,root);p.start();self.addCleanup(p.stop)
  p=patch.object(reading,'PdfReader',return_value=Mock(pages=list(range(30))));p.start();self.addCleanup(p.stop)
  self.now=datetime(2026,1,1,12)
  p=patch.object(reading,'now_utc',side_effect=lambda:self.now);p.start();self.addCleanup(p.stop)
  with self.factory() as db:
   db.add(DigitalResource(title='Reading fixture',author='Author',file_url='/digital-resources/files/'+filename,access_type='free',is_published=True,reviewed_by=1));db.commit()
 def start(self):
  r=self.client.post('/reading/sessions/1',headers=self.student);self.assertEqual(r.status_code,200,r.text);return r.json()['session_id']
 def ping(self,sid,seq,page=1,active=True,seconds=30):
  self.now+=timedelta(seconds=seconds)
  return self.client.post(f'/reading/sessions/{sid}/heartbeat',headers=self.student,json={'sequence':seq,'page':page,'active':active})
 def test_opening_idle_replay_and_owner_protection(self):
  sid=self.start()
  with self.factory() as db:self.assertEqual(db.query(XPTransaction).count(),0)
  self.assertEqual(self.ping(sid,1,active=False).json()['duration_seconds'],0)
  self.assertEqual(self.ping(sid,2,seconds=5).json()['duration_seconds'],0)
  self.assertEqual(self.ping(sid,3,seconds=100).json()['duration_seconds'],0)
  self.assertTrue(self.ping(sid,3).json()['duplicate'])
  self.assertEqual(self.ping(sid,4,page=999).status_code,422)
  self.assertEqual(self.client.post(f'/reading/sessions/{sid}/heartbeat',headers=self.staff,json={'sequence':4,'page':1,'active':True}).status_code,404)
  self.start();self.assertEqual(self.ping(sid,4).status_code,409)
 def test_duration_rewards_daily_cap_and_streak_gap(self):
  for offset in (0,1,3):
   self.now=datetime(2026,1,1+offset,12);sid=self.start()
   for seq in range(1,33):self.assertEqual(self.ping(sid,seq).status_code,200)
  with self.factory() as db:
   self.assertEqual(db.query(XPTransaction).filter_by(event_type='READING').count(),3)
   self.assertEqual(db.query(XPTransaction).filter_by(event_type='STREAK').count(),1)
  data=self.client.get('/reading/summary',headers=self.student).json()
  self.assertEqual(data['current_streak'],1);self.assertEqual(data['longest_streak'],2)
 def test_ten_distinct_pages_qualify_without_repeated_page_farming(self):
  sid=self.start();seq=0
  for page in range(1,11):
   for _ in range(2):seq+=1;result=self.ping(sid,seq,page=page)
  self.assertTrue(result.json()['qualified']);self.assertEqual(result.json()['pages_read'],10)
  for _ in range(3):seq+=1;result=self.ping(sid,seq,page=10)
  self.assertEqual(result.json()['pages_read'],10)
  with self.factory() as db:self.assertEqual(db.query(XPTransaction).count(),1)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
