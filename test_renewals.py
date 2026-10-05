from datetime import datetime, timedelta
from uuid import uuid4
from test_catalog_management import CatalogTests
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.loan_renewal import LoanRenewal
from app.routers.renewals import router

class RenewalTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(router)
  self.due=datetime.now().replace(microsecond=0)+timedelta(days=7)
  with self.factory() as db:
   db.add(BorrowRecord(user_id=2,book_id=1,status='borrowed',due_date=self.due));db.commit()
 def payload(self,due=None):return {'request_id':str(uuid4()),'expected_due_date':(due or self.due).isoformat()}
 def test_renew_retry_history_and_limit(self):
  payload=self.payload();r=self.client.post('/admin/loans/1/renew',headers=self.staff,json=payload)
  self.assertEqual(r.status_code,200);new=datetime.fromisoformat(r.json()['new_due_date'])
  self.assertEqual(new,self.due+timedelta(days=14))
  self.assertEqual(self.client.post('/admin/loans/1/renew',headers=self.staff,json=payload).json()['id'],r.json()['id'])
  self.assertEqual(len(self.client.get('/admin/loans/1/renewals',headers=self.staff).json()),1)
  self.assertEqual(self.client.post('/admin/loans/1/renew',headers=self.staff,json=self.payload()).status_code,409)
  r=self.client.post('/admin/loans/1/renew',headers=self.staff,json=self.payload(new));self.assertEqual(r.status_code,200)
  self.assertEqual(self.client.post('/admin/loans/1/renew',headers=self.staff,json=self.payload(datetime.fromisoformat(r.json()['new_due_date']))).status_code,409)
 def test_reject_student_returned_overdue_and_queue(self):
  self.assertEqual(self.client.post('/admin/loans/1/renew',headers=self.student,json=self.payload()).status_code,403)
  self.assertEqual(self.client.get('/admin/loans/1/renewals',headers=self.student).status_code,403)
  with self.factory() as db:
   db.add(Reservation(user_id=1,book_id=1,status='pending'));db.commit()
  self.assertEqual(self.client.post('/admin/loans/1/renew',headers=self.staff,json=self.payload()).status_code,409)
  with self.factory() as db:
   db.query(Reservation).delete();db.get(BorrowRecord,1).status='returned';db.commit()
  self.assertEqual(self.client.post('/admin/loans/1/renew',headers=self.staff,json=self.payload()).status_code,409)
  with self.factory() as db:
   loan=db.get(BorrowRecord,1);loan.status='borrowed';loan.due_date=datetime.now()-timedelta(days=1);due=loan.due_date;db.commit()
  self.assertEqual(self.client.post('/admin/loans/1/renew',headers=self.staff,json=self.payload(due)).status_code,409)

 # Base cases have their own dedicated fixtures and run in test_catalog_management.
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
