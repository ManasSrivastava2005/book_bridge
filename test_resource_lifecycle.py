from pathlib import Path
from fastapi.testclient import TestClient
from test_ebooks import EbookTests
from app.models.digital_resource import DigitalResource
from app.services.protected_uploads import ProtectedUploads

class LifecycleTests(EbookTests):
    def test_archive_restore_publish_persistence(self):
        row=self.upload().json();rid=row['id'];url=row['file_url']
        endpoint=f'/admin/digital-resources/{rid}/lifecycle'
        self.assertEqual(self.client.patch(endpoint,headers=self.student,json={'action':'publish'}).status_code,403)
        for action,published in [('publish',True),('unpublish',False),('archive',False),('restore',False),('publish',True)]:
            r=self.client.patch(endpoint,headers=self.staff,json={'action':action})
            self.assertEqual(r.status_code,200,r.text)
            # A fresh client/session observes the committed result.
            with TestClient(self.client.app) as fresh:
                self.assertEqual(fresh.get(url,headers=self.student).status_code,200 if published else 404)
                self.assertEqual(any(x['id']==rid for x in fresh.get('/digital-resources/').json()),published)
            with self.factory() as db:self.assertEqual(db.get(DigitalResource,rid).is_published,published)
            if action=='archive':self.assertEqual(self.client.patch(endpoint,headers=self.staff,json={'action':'publish'}).status_code,409)
        self.assertTrue((self.directory/url.rsplit('/',1)[-1]).exists())

    def test_legacy_static_file_privacy(self):
        (self.directory/'legacy.pdf').write_bytes(self.pdf)
        with self.factory() as db:
            r=DigitalResource(title='Legacy',author='Author',file_url='/uploads/legacy.pdf',is_published=False,distribution_basis='permission',rights_evidence='Original fixture permitted for testing',license_name='Permission')
            db.add(r);db.commit();rid=r.id
        self.client.app.mount('/uploads',ProtectedUploads(directory=str(self.directory),session_factory=self.factory))
        self.assertEqual(self.client.get('/uploads/legacy.pdf').status_code,401)
        self.assertEqual(self.client.get('/uploads/legacy.pdf',headers=self.student).status_code,404)
        self.assertEqual(self.client.get('/uploads/legacy.pdf',headers=self.staff).status_code,200)
        self.client.patch(f'/admin/digital-resources/{rid}/lifecycle',headers=self.staff,json={'action':'publish'})
        self.assertEqual(self.client.get('/uploads/legacy.pdf',headers=self.student).status_code,200)
        self.client.patch(f'/admin/digital-resources/{rid}/lifecycle',headers=self.staff,json={'action':'archive'})
        self.assertEqual(self.client.get('/uploads/legacy.pdf',headers=self.student).status_code,404)

    def test_missing_file_does_not_publish(self):
        row=self.upload().json();(self.directory/row['file_url'].rsplit('/',1)[-1]).unlink()
        self.assertEqual(self.client.patch(f"/admin/digital-resources/{row['id']}/lifecycle",headers=self.staff,json={'action':'publish'}).status_code,409)
        with self.factory() as db:self.assertFalse(db.get(DigitalResource,row['id']).is_published)
