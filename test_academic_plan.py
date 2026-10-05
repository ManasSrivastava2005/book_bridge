from datetime import date,timedelta
from unittest.mock import patch
from test_academic_profile import AcademicTests
from app.routers import academic_plan
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.academic_profile import AcademicProfile
from app.models.student_exam import StudentExam
from app.models.academic_task import AcademicTask
from app.services import academic_plan as service
class PlanTests(AcademicTests):
 def test_capacity_missed_days_preserve_completed_and_ownership(self):
  self.client.app.include_router(academic_plan.router)
  today=date(2026,10,1)
  with self.factory() as db:
   c=Curriculum(family='plan',title='CS',college='Uni',program='Degree',branch='CS',semester=1);db.add(c);db.flush()
   s=CurriculumNode(curriculum_id=c.id,kind='subject',title='OS');db.add(s);db.flush()
   u=CurriculumNode(curriculum_id=c.id,parent_id=s.id,kind='unit',title='Memory');db.add(u);db.flush()
   for i in range(5):db.add(CurriculumNode(curriculum_id=c.id,parent_id=u.id,kind='topic',title=f'Topic {i}'))
   db.add(AcademicProfile(user_id=2,curriculum_id=c.id,subject_ids=[s.id],custom_subjects=[]))
   db.add(StudentExam(user_id=2,subject_id=s.id,name='CAT',exam_type='CAT-I',date=today));db.commit()
  with patch.object(service,'today_utc',return_value=today):
   result=self.client.get('/academic/plan?daily_minutes=30',headers=self.student)
   self.assertEqual(result.status_code,200,result.text);data=result.json();self.assertTrue(data['warning']);self.assertGreater(data['unscheduled_tasks'],0)
   first=next(t for t in data['tasks'] if t['due_date'] and t['kind']=='practice');tid=first['id']
   self.assertEqual(self.client.put(f'/academic/plan/tasks/{tid}?completed=true',headers=self.staff).status_code,403)
   self.assertEqual(self.client.put(f'/academic/plan/tasks/{tid}?completed=true',headers=self.student).status_code,200)
  with patch.object(service,'today_utc',return_value=today+timedelta(days=1)):
   data=self.client.get('/academic/plan?daily_minutes=30',headers=self.student).json()
   same=next(t for t in data['tasks'] if t['id']==tid);self.assertTrue(same['completed']);self.assertEqual(same['due_date'],today.isoformat())
   self.assertTrue(all(t['due_date'] is None or t['due_date']>today.isoformat() for t in data['tasks'] if not t['completed']))
   for day in {t['due_date'] for t in data['tasks'] if not t['completed'] and t['due_date']}:
    self.assertLessEqual(sum(t['estimated_minutes'] for t in data['tasks'] if not t['completed'] and t['due_date']==day),30)
 test_old_accounts_and_optional_signup=None
 test_profile_validation_and_owner_scope=None
