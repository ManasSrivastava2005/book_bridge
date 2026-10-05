from test_staff_operations import StaffTests
class DraftReproduction(StaffTests):
 def test_legacy_external_draft_retained_but_publication_requires_curation(self):
  payload={'title':'External draft fixture','author':'Author','resource_type':'open_access','access_type':'free','provider':'Legacy provider','library_id':None,'external_url':'https://example.com/book','license_name':'Open access','is_published':False}
  r=self.client.post('/digital-resources/',headers=self.staff,json=payload);self.assertEqual(r.status_code,201,r.text)
  resource=r.json();rid=resource['id']
  r=self.client.put(f'/admin/digital-resources/{rid}',headers=self.staff,json={**resource,'is_published':True})
  self.assertEqual(r.status_code,422,r.text)
  self.assertEqual(self.client.get(f'/digital-resources/{rid}',headers=self.student).status_code,404)
  self.assertEqual(self.client.get(f'/digital-resources/{rid}',headers=self.staff).status_code,200)
  # Original B2 baseline passed before the explicit B7 curation requirement.
if __name__=='__main__':
 import unittest
 unittest.main()
