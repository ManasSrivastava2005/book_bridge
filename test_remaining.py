"""Notifications, private rooms, attachments and moderation regressions."""
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from datetime import datetime,timedelta
from sqlalchemy import inspect
from app.models.study import StudyRoom,StudyMember,StudyMessage,StudyAudit,StudyReport,StudyAttachment
from app.models.notification import Notification
from app.models.borrow import BorrowRecord
from app.models.book import Book
from app.models.overdue_reminder import OverdueReminder
from app.routers import study,notifications
from test_study import StudyTests
from app.database import Base
from migrate_remaining import migrate

class RemainingTests(StudyTests):
 def setUp(self):
  super().setUp()
  Base.metadata.create_all(self.engine,tables=[Book.__table__,BorrowRecord.__table__,OverdueReminder.__table__])
  self.client.app.include_router(notifications.router)
  temporary=TemporaryDirectory();self.addCleanup(temporary.cleanup);self.directory=Path(temporary.name)
  patcher=patch.object(study,'ATTACHMENT_DIR',self.directory);patcher.start();self.addCleanup(patcher.stop)
 def test_private_invite_cannot_be_guessed_or_seen_in_directory(self):
  res=self.client.post('/study/rooms',headers=self.headers(),json={'title':'Private','subject':'CS','is_private':True})
  self.assertEqual(res.status_code,201,res.text);room=res.json();rid=room['id'];code=room['invite_code'];self.assertTrue(code)
  self.assertEqual(self.client.get('/study/rooms',headers=self.headers(2)).json()['items'],[])
  self.assertEqual(self.client.get(f'/study/rooms/{rid}',headers=self.headers(2)).status_code,404)
  self.assertEqual(self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2)).status_code,404)
  preview=self.client.get(f'/study/rooms/{rid}',params={'invite':code},headers=self.headers(2)).json()
  self.assertIsNone(preview['invite_code'])
  self.assertEqual(self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers(2)).status_code,403)
  self.assertEqual(self.client.post(f'/study/rooms/{rid}/join',params={'invite':code},headers=self.headers(2)).status_code,200)
  self.assertEqual(self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers(2)).status_code,200)
 def test_attachments_membership_cleanup_and_archive(self):
  rid=self.room()
  def upload(user=1,content=b'shared study',name='study.txt'):
   return self.client.post(f'/study/rooms/{rid}/attachments',headers=self.headers(user),files={'file':(name,content,'text/plain')})
  self.assertEqual(upload(2).status_code,403)
  self.assertEqual(upload(content=b'').status_code,400)
  self.assertEqual(upload(name='bad.exe').status_code,400)
  response=upload(name='../../study.txt');self.assertEqual(response.status_code,201,response.text);aid=response.json()['id']
  url=f'/study/rooms/{rid}/attachments/{aid}'
  self.assertEqual(self.client.get(url).status_code,401)
  self.assertEqual(self.client.get(url,headers=self.headers(2)).status_code,403)
  self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2))
  self.assertEqual(self.client.get(url,headers=self.headers(2)).content,b'shared study')
  self.assertEqual(self.client.delete(url,headers=self.headers(2)).status_code,403)
  self.client.patch(f'/study/rooms/{rid}',headers=self.headers(),json={'archived':True})
  self.assertEqual(upload().status_code,409)
  self.assertEqual(self.client.delete(url,headers=self.headers()).status_code,204)
  self.assertEqual(list(self.directory.iterdir()),[])
 def test_reports_audit_staff_scope_and_post_notifications(self):
  rid=self.room();self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2))
  key='93b54256-0f62-4ea6-aec4-76b97cebd111';message=self.post(rid,client_id=key).json()['id'];self.post(rid,client_id=key)
  with self.factory() as db:self.assertEqual(db.query(Notification).filter(Notification.user_id==2).count(),1)
  report=f'/study/rooms/{rid}/messages/{message}/report'
  self.assertEqual(self.client.post(report,headers=self.headers(3),json={'reason':'Concern'}).status_code,403)
  for _ in range(2):self.assertEqual(self.client.post(report,headers=self.headers(2),json={'reason':'Please review'}).status_code,201)
  for path in ['/study/reports','/study/audit']:
   self.assertEqual(self.client.get(path,headers=self.headers(2)).status_code,403)
   self.assertEqual(self.client.get(path,headers=self.headers(4)).status_code,200)
  reports=self.client.get('/study/reports',headers=self.headers(4)).json();self.assertEqual(len(reports),1)
  self.assertEqual(self.client.delete(f'/study/rooms/{rid}/messages/{message}',headers=self.headers(4)).status_code,204)
  self.assertEqual(self.client.post(f'/study/reports/{reports[0]["id"]}/resolve',headers=self.headers(4)).status_code,200)
  self.assertEqual(self.client.get('/study/reports',headers=self.headers(4)).json(),[])
  with self.factory() as db:self.assertEqual(db.query(StudyAudit).filter(StudyAudit.action=='remove_message').count(),1)
 def test_limits_and_retry_after_limit(self):
  rid=self.room()
  last=None
  for i in range(20):
   key=f'00000000-0000-0000-0000-{i:012d}';res=self.post(rid,body='Message '+str(i),client_id=key);self.assertEqual(res.status_code,201);last=(key,i)
  blocked=self.post(rid);self.assertEqual(blocked.status_code,429);self.assertIn('retry-after',blocked.headers)
  self.assertEqual(self.post(rid,body='Message '+str(last[1]),client_id=last[0]).status_code,201)
 def test_daily_reminders_deduplicate_stop_after_return_and_scope_read(self):
  with self.factory() as db:
   book=Book(title='Overdue fixture',author='Author');db.add(book);db.flush()
   loan=BorrowRecord(user_id=1,book_id=book.id,status='borrowed',due_date=datetime.utcnow()-timedelta(days=2));db.add(loan);db.commit();lid=loan.id
  for _ in range(2):
   self.assertEqual(self.client.get('/notifications/unread-count',headers=self.headers()).json()['count'],1)
  notices=self.client.get('/notifications/',headers=self.headers()).json();self.assertEqual(len(notices),1)
  nid=notices[0]['id']
  self.assertEqual(self.client.put(f'/notifications/{nid}/read',headers=self.headers(2)).status_code,404)
  self.assertEqual(self.client.put(f'/notifications/{nid}/read',headers=self.headers()).status_code,200)
  self.assertEqual(self.client.get('/notifications/unread-count',headers=self.headers()).json()['count'],0)
  self.assertEqual(self.client.get('/notifications/',headers=self.headers(2)).json(),[])
  with self.factory() as db:
   db.get(BorrowRecord,lid).status='returned';db.commit()
  self.assertEqual(len(self.client.get('/notifications/',headers=self.headers()).json()),1)
  with self.factory() as db:self.assertEqual(db.query(OverdueReminder).count(),1)
 def test_remaining_migration_idempotent(self):
  rid=self.room()
  with self.engine.begin() as connection:migrate(connection);migrate(connection)
  with self.factory() as db:self.assertIsNotNone(db.get(StudyRoom,rid))
