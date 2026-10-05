from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.database import get_db
from test_staff_operations import StaffTests
from app.routers import academic,personal_curriculum,curriculum
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.topic_progress import TopicProgress
from app.models.academic_profile import AcademicProfile

class PersonalCurriculumTests(StaffTests):
 def setUp(self):
  super().setUp()
  app=FastAPI()
  for router in [academic.router,personal_curriculum.router,curriculum.router]:app.include_router(router)
  def dependency():
   with self.factory() as db:yield db
  app.dependency_overrides[get_db]=dependency
  self.academic_client=TestClient(app);self.addCleanup(self.academic_client.close)
  self.tree={'title':'Personal CS','subjects':[{'title':'Operating Systems','children':[{'title':'Memory','children':[{'title':'Paging','objectives':'Explain page tables','subtopics':['TLB'],'children':[]}]}]}]}
 def save(self,payload=None,headers=None):return self.academic_client.put('/academic/personal-curriculum',headers=headers or self.student,json=payload or self.tree)
 def test_owner_only_and_public_staff_catalog_exclusion(self):
  response=self.save();self.assertEqual(response.status_code,200,response.text);tree=response.json();cid=tree['curriculum_id']
  self.assertEqual(self.academic_client.get('/academic/catalog').json(),[])
  self.assertEqual(len(self.academic_client.get('/academic/catalog',headers=self.student).json()),1)
  self.assertEqual(self.academic_client.get('/academic/catalog',headers=self.waiting).json(),[])
  self.assertEqual(self.academic_client.get('/admin/curricula',headers=self.staff).json(),[])
  self.assertEqual(self.academic_client.get(f'/admin/curricula/{cid}',headers=self.staff).status_code,404)
  self.assertEqual(self.save(headers=self.staff).status_code,403)
  self.assertEqual(self.save(tree,headers=self.waiting).status_code,404)
  self.assertEqual(self.academic_client.put('/academic/profile',headers=self.waiting,json={'curriculum_id':cid,'subject_ids':[]}).status_code,422)
 def test_edits_preserve_ids_progress_and_archive_removed_topics(self):
  tree=self.save().json();topic=tree['subjects'][0]['children'][0]['children'][0];tid=topic['id']
  self.assertEqual(self.academic_client.put(f'/academic/topics/{tid}/completion?completed=true',headers=self.student).status_code,200)
  topic['title']='Virtual memory paging'
  updated=self.save(tree);self.assertEqual(updated.status_code,200,updated.text)
  self.assertEqual(updated.json()['subjects'][0]['children'][0]['children'][0]['id'],tid)
  with self.factory() as db:self.assertIsNotNone(db.get(TopicProgress,(2,tid)))
  self.assertEqual(self.save(tree).status_code,409)
  tree=updated.json();tree['subjects'][0]['children'][0]['children']=[]
  self.assertEqual(self.save(tree).status_code,200)
  with self.factory() as db:
   self.assertTrue(db.get(CurriculumNode,tid).archived);self.assertIsNotNone(db.get(TopicProgress,(2,tid)))
  self.assertEqual(self.academic_client.put(f'/academic/topics/{tid}/completion?completed=false',headers=self.student).status_code,404)
 def test_foreign_node_and_invalid_depth_rejected_without_partial_changes(self):
  mine=self.save().json();other=self.save(headers=self.waiting).json()
  mine['subjects'][0]['id']=other['subjects'][0]['id']
  self.assertEqual(self.save(mine).status_code,422)
  actual=self.academic_client.get('/academic/personal-curriculum',headers=self.student).json()
  self.assertEqual(actual['expected_version'],1)
  invalid={**self.tree,'subjects':[{'title':'S','children':[{'title':'U','children':[{'title':'T','children':[{'title':'Too deep'}]}]}]}]}
  self.assertEqual(self.save(invalid).status_code,422)
