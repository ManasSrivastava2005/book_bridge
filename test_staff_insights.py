from datetime import datetime,timedelta
from test_catalog_management import CatalogTests
from app.routers import insights,notes,question_banks
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.borrow import BorrowRecord
from app.models.resource_usage import ResourceUsage

class InsightsTests(CatalogTests):
 def setUp(self):
  super().setUp()
  for r in (insights.router,notes.router,question_banks.router):self.client.app.include_router(r)
 def test_real_counts_and_uncollected_values(self):
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,status='borrowed',due_date=datetime.now()-timedelta(days=1)))
   db.add(Note(user_id=2,title='Published',subject='OS',status='published',file_url='/uploads/fixture.pdf',download_count=3))
   db.add(Note(user_id=2,title='Private',subject='OS',status='personal',download_count=99))
   db.add(QuestionBank(title='Exam',subject='OS',semester=5,branch='CSE',file_url='/uploads/exam.pdf',download_count=2));db.commit()
  self.assertEqual(self.client.post('/notes/1/download').status_code,200)
  self.assertEqual(self.client.post('/notes/2/download').status_code,404)
  self.assertEqual(self.client.post('/question-banks/1/download').status_code,200)
  r=self.client.get('/admin/insights',headers=self.staff);self.assertEqual(r.status_code,200);d=r.json()
  self.assertEqual(d['current_overdue_rate'],100)
  self.assertEqual(d['note_download_counter'],4);self.assertEqual(d['question_bank_download_counter'],3)
  self.assertEqual(d['download_requests'],{'note':1,'question_bank':1})
  self.assertIsNone(d['quiz_participation']);self.assertIsNone(d['reading_time'])
  self.assertEqual(d['top_books'][0]['count'],1)
  self.assertEqual(self.client.get('/admin/insights',headers=self.student).status_code,403)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
