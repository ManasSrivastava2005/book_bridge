import tempfile
from pathlib import Path
from datetime import date,timedelta
from uuid import uuid4
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.database import get_db
from app.routers import curriculum_workspace,personal_curriculum,academic,student_exams,syllabus
from app.models.curriculum import CurriculumNode
from app.models.syllabus_upload import SyllabusUpload
from app.models.academic_task import AcademicTask
from app.schemas.personal_curriculum import PersonalCurriculumWrite
from test_staff_operations import StaffTests
from test_syllabus_processing import text_pdf

class WorkspaceTests(StaffTests):
 def test_delete_subject_removes_card_preserves_history_and_other_semesters(self):
  from app.models.topic_progress import TopicProgress
  from app.models.academic_profile import AcademicProfile
  from app.models.student_exam import StudentExam
  tree=self.populated();subject=tree['subjects'][0];sid=subject['id'];tid=subject['children'][0]['children'][0]['id']
  tree=self.add('Sibling');sibling=tree['subjects'][1]['id']
  self.web.put(f'/academic/topics/{tid}/completion?completed=true',headers=self.student)
  self.web.post('/academic/exams',headers=self.student,json={'subject_id':sid,'name':'Exam','exam_type':'CAT-I','date':str(date.today()),'topic_ids':[tid]})
  upload=self.web.post('/academic/syllabi',headers=self.student,data={'request_id':str(uuid4()),'subject_id':sid},files={'file':('syllabus.pdf',text_pdf(['UNIT 1','Paging']),'application/pdf')}).json()
  later=self.add('Later semester',4)
  url=f'/academic/subjects/{sid}?expected_version={tree["expected_version"]}'
  for headers,expected in [(self.waiting,404),(self.staff,403),({},401)]:self.assertEqual(self.web.delete(url,headers=headers).status_code,expected)
  self.assertEqual(self.web.delete(f'/academic/subjects/{sid}?expected_version=1',headers=self.student).status_code,409)
  self.assertEqual(self.web.delete(url,headers=self.student).status_code,204)
  self.assertEqual([s['id'] for s in self.workspace(3)['subjects']],[sibling]);self.assertEqual(len(self.workspace(4)['subjects']),1)
  self.assertEqual(self.web.get(f'/academic/syllabi/{upload["id"]}/file',headers=self.student).status_code,404)
  with self.factory() as db:
   self.assertTrue(db.get(CurriculumNode,sid).archived);self.assertTrue(db.get(CurriculumNode,tid).archived)
   self.assertIsNotNone(db.get(TopicProgress,(2,tid)));self.assertEqual(db.query(StudentExam).count(),1)
   self.assertEqual(db.get(AcademicProfile,2).curriculum_id,later['curriculum_id'])
  recreated=self.add('Operating Systems');self.assertNotEqual(recreated['subjects'][-1]['id'],sid)
 def test_delete_only_empty_subject_leaves_empty_semester(self):
  from app.models.academic_profile import AcademicProfile
  tree=self.add();sid=tree['subjects'][0]['id']
  self.assertEqual(self.web.delete(f'/academic/subjects/{sid}?expected_version={tree["expected_version"]}',headers=self.student).status_code,204)
  self.assertEqual(self.workspace()['subjects'],[])
  self.assertEqual(self.workspace()['path']['steps'],[])
  with self.factory() as db:self.assertEqual(db.get(AcademicProfile,2).subject_ids,[])
 def setUp(self):
  super().setUp()
  app=FastAPI()
  for module in [curriculum_workspace,personal_curriculum,academic,student_exams,syllabus]:app.include_router(module.router)
  def dependency():
   with self.factory() as db:yield db
  app.dependency_overrides[get_db]=dependency
  self.web=TestClient(app);self.addCleanup(self.web.close)
  folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
  p=patch.object(syllabus,'PRIVATE_SYLLABUS_DIR',Path(folder.name));p.start();self.addCleanup(p.stop)
 def add(self,name='Operating Systems',semester=3):
  r=self.web.post('/academic/subjects',headers=self.student,json={'title':name,'semester':semester})
  self.assertEqual(r.status_code,201,r.text);return r.json()
 def workspace(self,semester=3):return self.web.get(f'/academic/workspace?semester={semester}',headers=self.student).json()
 def populated(self):
  tree=self.add();subject=tree['subjects'][0]
  subject['children']=[{'title':'Processes','children':[{'title':t} for t in ['Threads','Scheduling','Deadlocks','File systems']]}]
  r=self.web.put(f"/academic/subjects/{subject['id']}",headers=self.student,json={'expected_version':tree['expected_version'],'subject':subject})
  self.assertEqual(r.status_code,200,r.text)
  return r.json()
 def test_multiple_semesters_siblings_and_no_subject_count_limit(self):
  first=self.add();sid=first['subjects'][0]['id'];self.add('Data Structures');self.add('Mathematics',4)
  self.assertEqual(len(self.workspace(3)['subjects']),2);self.assertEqual(len(self.workspace(4)['subjects']),1)
  self.assertEqual(self.workspace(3)['subjects'][0]['id'],sid)
  tree=PersonalCurriculumWrite(title='Many',semester=5,subjects=[{'title':f'Subject {i}'} for i in range(110)])
  r=self.web.put('/academic/personal-curriculum',headers=self.student,json=tree.model_dump());self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(len(r.json()['subjects']),110)
 def test_subject_ownership_and_stale_write(self):
  tree=self.populated();s=tree['subjects'][0];payload={'expected_version':tree['expected_version'],'subject':s}
  for headers,expected in [(self.staff,403),(self.waiting,404),({},401)]:
   r=self.web.put(f"/academic/subjects/{s['id']}",headers=headers,json=payload);self.assertEqual(r.status_code,expected)
  self.add('Sibling')
  self.assertEqual(self.web.put(f"/academic/subjects/{s['id']}",headers=self.student,json=payload).status_code,409)
 def test_foreign_topic_coverage_rejected_and_multiple_exams_scoped(self):
  tree=self.populated();s=tree['subjects'][0];ids=[t['id'] for t in s['children'][0]['children']]
  payload={'subject_id':s['id'],'name':'CAT-II','exam_type':'CAT-II','date':str(date.today()+timedelta(days=1)),'topic_ids':[ids[2]]}
  r=self.web.post('/academic/exams',headers=self.student,json=payload);self.assertEqual(r.status_code,201,r.text)
  later={**payload,'name':'End Semester','date':str(date.today()+timedelta(days=10)),'topic_ids':[ids[0],ids[1]]}
  self.assertEqual(self.web.post('/academic/exams',headers=self.student,json=later).status_code,201)
  for headers,values in [(self.waiting,payload),(self.student,{**payload,'topic_ids':[999999]})]:
   self.assertIn(self.web.post('/academic/exams',headers=headers,json=values).status_code,[404,422])
  path=self.web.get('/academic/learning-path',headers=self.student).json()['steps']
  self.assertEqual([s['id'] for s in path],[ids[2],ids[0],ids[1],ids[3]])
  self.assertIsNone(path[-1]['exam_date'])
 def test_study_time_changes_schedule_and_completion_reschedules(self):
  tree=self.populated();sid=tree['subjects'][0]['id']
  self.assertEqual(self.web.put('/academic/study-time',headers=self.student,json={'daily_minutes':15}).status_code,200)
  slow=self.web.get('/academic/learning-path',headers=self.student).json()
  self.assertNotEqual(slow['steps'][0]['scheduled_date'],slow['steps'][1]['scheduled_date'])
  self.assertEqual(slow['steps'][0]['session_minutes'],15)
  self.web.put('/academic/study-time',headers=self.student,json={'daily_minutes':120})
  fast=self.web.get('/academic/learning-path',headers=self.student).json()
  self.assertEqual(fast['steps'][0]['scheduled_date'],fast['steps'][-1]['scheduled_date'])
  tid=fast['steps'][0]['id'];self.web.put(f'/academic/topics/{tid}/completion?completed=true',headers=self.student)
  updated=self.web.get('/academic/learning-path',headers=self.student).json()
  self.assertEqual(updated['steps'][-1]['id'],tid);self.assertEqual(updated['steps'][-1]['status'],'completed')
  self.assertEqual(self.workspace()['daily_minutes'],120)
  with self.factory() as db:
   self.assertEqual(db.query(AcademicTask).count(),0)
   from app.services.missions import daily_missions
   mission=next(m for m in daily_missions(db,2) if m['id']=='academic')
   self.assertTrue(mission['completed']);self.assertEqual(mission['xp'],0)
 def test_subject_upload_review_preserves_other_subjects_private_and_idempotent(self):
  tree=self.populated();sid=tree['subjects'][0]['id'];tree=self.add('Data Structures');other=tree['subjects'][1]['id']
  pdf=text_pdf(['UNIT 1','Processes','Threads','UNIT 2','CPU Scheduling','Scheduling Algorithms'])
  r=self.web.post('/academic/syllabi',headers=self.student,data={'request_id':str(uuid4()),'subject_id':sid},files={'file':('os.pdf',pdf,'application/pdf')})
  self.assertEqual(r.status_code,201,r.text);row=r.json();rid=row['id']
  self.assertEqual(self.workspace()['subjects'][0]['total_topics'],4)
  candidate={**tree['subjects'][0],'children':row['proposal']['subjects'][0]['children']}
  self.assertEqual(candidate['children'][1]['children'][0]['title'],'CPU Scheduling')
  payload={'expected_version':tree['expected_version'],'subject':candidate}
  for headers,expected in [(self.waiting,404),(self.staff,403),({},401)]:
   self.assertEqual(self.web.get(f'/academic/syllabi/{rid}/file',headers=headers).status_code,expected)
  self.assertEqual(self.web.post(f'/academic/syllabi/{rid}/confirm-subject/{other}',headers=self.student,json=payload).status_code,409)
  for _ in range(2):
   r=self.web.post(f'/academic/syllabi/{rid}/confirm-subject/{sid}',headers=self.student,json=payload);self.assertEqual(r.status_code,200,r.text)
  result=self.workspace();self.assertEqual([s['id'] for s in result['subjects']],[sid,other])
  self.assertEqual(result['subjects'][0]['total_topics'],4)
  self.assertEqual(self.web.get(f'/academic/syllabi/{rid}/file',headers=self.student).content,pdf)
 def test_cannot_move_node_between_subjects(self):
  tree=self.populated();tree=self.add('Another');first,second=tree['subjects'];second['children']=first['children']
  r=self.web.put(f"/academic/subjects/{second['id']}",headers=self.student,json={'expected_version':tree['expected_version'],'subject':second})
  self.assertEqual(r.status_code,422)
 def test_legacy_upload_retained_and_can_be_confirmed_into_subject(self):
  r=self.web.post('/academic/syllabi',headers=self.student,data={'request_id':str(uuid4())},files={'file':('old.pdf',text_pdf(['Course: OS','Unit 1: Memory','Topic: Paging']),'application/pdf')})
  row=r.json();tree=self.add();subject=tree['subjects'][0];subject['children']=row['proposal']['subjects'][0]['children']
  r=self.web.post(f"/academic/syllabi/{row['id']}/confirm-subject/{subject['id']}",headers=self.student,json={'expected_version':tree['expected_version'],'subject':subject})
  self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(r.json()['subject_id'],subject['id'])
 def test_delete_upload_owner_only_revokes_access_and_removes_file(self):
  key=str(uuid4());pdf=text_pdf(['Course: OS','Unit 1: Memory','Topic: Paging'])
  def upload():return self.web.post('/academic/syllabi',headers=self.student,data={'request_id':key},files={'file':('old.pdf',pdf,'application/pdf')})
  rid=upload().json()['id'];url=f'/academic/syllabi/{rid}'
  with self.factory() as db:path=syllabus.PRIVATE_SYLLABUS_DIR/db.get(SyllabusUpload,rid).filename
  self.assertTrue(path.exists())
  for headers,expected in [(self.waiting,404),(self.staff,403),({},401)]:
   self.assertEqual(self.web.delete(url,headers=headers).status_code,expected)
  for _ in range(2):self.assertEqual(self.web.delete(url,headers=self.student).status_code,204)
  self.assertFalse(path.exists())
  for suffix in ['', '/file']:self.assertEqual(self.web.get(url+suffix,headers=self.student).status_code,404)
  self.assertEqual(self.web.get('/academic/syllabi',headers=self.student).json(),[])
  self.assertEqual(upload().status_code,410)
  with self.factory() as db:
   row=db.get(SyllabusUpload,rid);self.assertEqual(row.extracted_text,'');self.assertEqual(row.proposal,{})
 def test_delete_curriculum_preserves_subjects_exams_and_historical_progress(self):
  from app.models.topic_progress import TopicProgress
  from app.models.student_exam import StudentExam
  tree=self.populated();subject=tree['subjects'][0];sid=subject['id'];tid=subject['children'][0]['children'][0]['id']
  tree=self.add('Other subject');other=tree['subjects'][1]['id']
  self.web.put(f'/academic/topics/{tid}/completion?completed=true',headers=self.student)
  self.web.post('/academic/exams',headers=self.student,json={'subject_id':sid,'name':'CAT','exam_type':'CAT-I','date':str(date.today()),'topic_ids':[tid]})
  upload=self.web.post('/academic/syllabi',headers=self.student,data={'request_id':str(uuid4()),'subject_id':sid},files={'file':('syllabus.pdf',text_pdf(['UNIT 1','Paging']),'application/pdf')}).json()
  url=f'/academic/subjects/{sid}/curriculum?expected_version={tree["expected_version"]}'
  for headers,expected in [(self.waiting,404),(self.staff,403),({},401)]:self.assertEqual(self.web.delete(url,headers=headers).status_code,expected)
  self.assertEqual(self.web.delete(url,headers=self.student).status_code,204)
  result=self.workspace();self.assertEqual([s['id'] for s in result['subjects']],[sid,other]);self.assertEqual(result['subjects'][0]['total_topics'],0)
  self.assertEqual(self.web.delete(url,headers=self.student).status_code,409)
  self.assertEqual(self.web.get(f'/academic/syllabi/{upload["id"]}/file',headers=self.student).status_code,404)
  with self.factory() as db:
   self.assertIsNotNone(db.get(TopicProgress,(2,tid)));self.assertTrue(db.get(CurriculumNode,tid).archived);self.assertEqual(db.query(StudentExam).count(),1)
