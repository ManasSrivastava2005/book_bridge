from test_catalog_management import CatalogTests
from app.routers.curriculum import router
from app.models.curriculum import Curriculum, CurriculumNode, CurriculumResource

class CurriculumTests(CatalogTests):
 def setUp(self):
  super().setUp();self.client.app.include_router(router)
  self.payload={'title':'CS 2026','college':'Test University','program':'BTech','branch':'CSE','semester':5}
  self.cid=self.client.post('/admin/curricula',headers=self.staff,json=self.payload).json()['id']
 def node(self,kind,title,parent=None,cid=None):
  r=self.client.post(f'/admin/curricula/{cid or self.cid}/nodes',headers=self.staff,json={'kind':kind,'title':title,'parent_id':parent})
  self.assertEqual(r.status_code,201);return r.json()['id']
 def test_tree_mapping_duplicate_and_archive(self):
  subject=self.node('subject','OS');unit=self.node('unit','Processes',subject);topic=self.node('topic','Scheduling',unit)
  for _ in range(2):self.assertEqual(self.client.post(f'/admin/curricula/topics/{topic}/resources',headers=self.staff,json={'kind':'book','resource_id':1}).status_code,201)
  copy=self.client.post(f'/admin/curricula/{self.cid}/duplicate',headers=self.staff)
  self.assertEqual(copy.status_code,201);self.assertEqual(copy.json()['version'],2)
  detail=self.client.get(f'/admin/curricula/{copy.json()["id"]}',headers=self.staff).json()
  self.assertEqual(len(detail['nodes']),3);self.assertEqual(len(detail['mappings']),1)
  self.assertNotEqual(detail['mappings'][0]['topic_id'],topic)
  self.client.patch(f'/admin/curricula/{self.cid}/archive',headers=self.staff,json={'archived':True})
  self.assertEqual(self.client.put(f'/admin/curricula/{self.cid}',headers=self.staff,json=self.payload).status_code,409)
  self.assertEqual(self.client.put(f'/admin/curricula/nodes/{topic}',headers=self.staff,json={'title':'Changed'}).status_code,409)
  self.assertEqual(self.client.get(f'/admin/curricula/{self.cid}',headers=self.staff).status_code,200)
 def test_roles_and_cross_curriculum_hierarchy(self):
  self.assertEqual(self.client.get('/admin/curricula',headers=self.student).status_code,403)
  self.assertEqual(self.client.post('/admin/curricula',headers=self.student,json=self.payload).status_code,403)
  subject=self.node('subject','OS')
  other=self.client.post('/admin/curricula',headers=self.staff,json={**self.payload,'college':'Other University'}).json()['id']
  self.assertEqual(self.client.post(f'/admin/curricula/{other}/nodes',headers=self.staff,json={'kind':'unit','title':'Invalid','parent_id':subject}).status_code,422)
  self.assertEqual(self.client.post(f'/admin/curricula/{self.cid}/nodes',headers=self.staff,json={'kind':'topic','title':'Invalid','parent_id':subject}).status_code,422)
 def test_node_edit_and_enrollment_idempotence(self):
  subject=self.node('subject','OS')
  self.assertEqual(self.client.put(f'/admin/curricula/nodes/{subject}',headers=self.staff,json={'title':'Operating Systems','code':'CS501'}).status_code,200)
  for _ in range(2):self.assertEqual(self.client.put(f'/admin/curricula/subjects/{subject}/students/2',headers=self.staff).status_code,200)
  self.assertEqual(len(self.client.get(f'/admin/curricula/{self.cid}',headers=self.staff).json()['enrollments']),1)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
