import io
from unittest.mock import patch
from PIL import Image
from test_ebooks import EbookTests
from app.models.digital_resource import DigitalResource
from app.routers import unified_search,ai,digital_resources

class CurationTests(EbookTests):
 def test_rights_required_legacy_retained_and_search_filtered(self):
  self.client.app.include_router(unified_search.router);self.client.app.include_router(ai.router)
  with self.factory() as db:
   legacy=DigitalResource(title='UnreviewedUnique',author='Author',is_published=True,external_url='https://example.com/book')
   db.add(legacy);db.commit();rid=legacy.id
  self.assertEqual(self.client.get(f'/digital-resources/{rid}',headers=self.student).status_code,404)
  self.assertEqual(self.client.get(f'/digital-resources/{rid}',headers=self.staff).status_code,200)
  self.assertEqual(self.client.get('/search/unified?query=UnreviewedUnique').json()['digital_resources'],[])
  for basis in ['public_domain','open_license','permission']:
   response=self.upload(payload={**self.payload,'distribution_basis':basis,'is_published':True})
   self.assertEqual(response.status_code,201,response.text)
   self.assertEqual(response.json()['reviewed_by'],1);self.assertIsNotNone(response.json()['reviewed_at'])
  for changes in [{'distribution_basis':None},{'rights_evidence':' '},{'license_name':''}]:
   self.assertEqual(self.upload(payload={**self.payload,**changes,'is_published':True}).status_code,422)
  with self.factory() as db:self.assertIsNotNone(db.get(DigitalResource,rid))

 def test_metadata_edit_requires_fresh_review_and_unsafe_cover_rejected(self):
  row=self.upload(payload={**self.payload,'is_published':True}).json()
  response=self.client.put(f"/admin/digital-resources/{row['id']}",headers=self.staff,json={**row,'is_published':False,'rights_evidence':''})
  self.assertEqual(response.status_code,200,response.text);self.assertIsNone(response.json()['reviewed_by'])
  self.assertEqual(self.client.patch(f"/admin/digital-resources/{row['id']}/lifecycle",headers=self.staff,json={'action':'publish'}).status_code,422)
  self.assertEqual(self.upload(payload={**self.payload,'cover_image':'javascript:alert(1)'}).status_code,422)

 def test_cover_upload_reencodes_and_is_staff_only(self):
  image=Image.new('RGB',(10,10),'blue');stream=io.BytesIO();image.save(stream,format='PNG')
  with patch.object(digital_resources,'COVER_DIR',self.directory):
   for headers,expected in [(self.student,403),(self.staff,201)]:
    response=self.client.post('/digital-resources/covers',headers=headers,files={'file':('cover.png',stream.getvalue(),'image/png')})
    self.assertEqual(response.status_code,expected,response.text)
   self.assertEqual(self.client.post('/digital-resources/covers',headers=self.staff,files={'file':('fake.png',b'not an image','image/png')}).status_code,400)
   with Image.open(next(self.directory.glob('*.jpg'))) as converted:self.assertEqual(converted.format,'JPEG')
