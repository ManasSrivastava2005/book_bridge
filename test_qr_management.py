import json,io
from PIL import Image
from test_catalog_management import CatalogTests
from app.routers.scanner import router
from app.services.qr_service import create_qr_payload
from app.models.book import Book

class QRTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(router)
  with self.factory() as db:
   b=db.get(Book,1);b.isbn='9780132350884';b.rack='CS-2';b.shelf='3';db.commit()
 def test_generation_roles_and_payload(self):
  for path in ('/books/1/qr','/books/1/sticker','/books/1/qr/data'):
   self.assertEqual(self.client.get(path,headers=self.student).status_code,403)
   self.assertEqual(self.client.get(path).status_code,401)
   self.assertEqual(self.client.get(path,headers=self.staff).status_code,200)
  with Image.open(io.BytesIO(self.client.get('/books/1/sticker',headers=self.staff).content)) as image:self.assertEqual(image.size,(560,300))
  payload=json.loads(create_qr_payload(1));self.assertTrue(payload['scan_url'].endswith('/books/1/scan'))
 def test_resolver_formats_and_unknown_codes(self):
  for raw in ('1','#1','978-0132350884','http://localhost/books/1/scan',create_qr_payload(1)):
   r=self.client.post('/scan/resolve',json={'scanned_payload':raw});self.assertEqual(r.status_code,200);self.assertEqual(r.json()['book']['id'],1)
  for raw in ('garbage1','{"book_id":true}','{"book_id":999999999999999999999999}'):
   self.assertEqual(self.client.post('/scan/resolve',json={'scanned_payload':raw}).status_code,400)
  self.assertEqual(self.client.post('/scan/resolve',json={'scanned_payload':'9780000000000'}).status_code,404)
  self.assertEqual(self.client.post('/scan/resolve',json={'scanned_payload':'{"book_id":999}'}).status_code,404)
 def test_missing_location_not_invented(self):
  with self.factory() as db:b=db.get(Book,1);b.rack=None;b.shelf=None;db.commit()
  r=self.client.get('/books/1/scan').json();self.assertEqual(r['location']['rack'],'Not recorded');self.assertEqual(r['book']['issued_copies'],0)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
