from datetime import datetime,timezone
from test_academic_profile import AcademicTests
from app.models.curriculum import Curriculum,CurriculumNode,CurriculumResource
from app.models.academic_profile import AcademicProfile
from app.models.student_exam import StudentExam
from app.models.book import Book
from app.routers import dashboard
class RecommendationTests(AcademicTests):
 def test_real_mapping_urgency_and_zero_reviews(self):
  self.client.app.include_router(dashboard.router)
  with self.factory() as db:
   c=Curriculum(family='recommend',title='CS',college='Uni',program='Degree',branch='CS',semester=1);db.add(c);db.flush()
   s=CurriculumNode(curriculum_id=c.id,kind='subject',title='OS');db.add(s);db.flush()
   u=CurriculumNode(curriculum_id=c.id,parent_id=s.id,kind='unit',title='Memory');db.add(u);db.flush()
   t=CurriculumNode(curriculum_id=c.id,parent_id=u.id,kind='topic',title='Paging');db.add(t);db.flush()
   db.add(CurriculumResource(topic_id=t.id,book_id=1));db.add(AcademicProfile(user_id=2,curriculum_id=c.id,subject_ids=[s.id],custom_subjects=[]))
   db.add(StudentExam(user_id=2,subject_id=s.id,name='CAT',exam_type='CAT-I',date=datetime.now(timezone.utc).date(),topic_ids=[t.id]))
   db.add(Book(title='Unmapped',author='Author',total_copies=1,available_copies=1));db.commit()
  r=self.client.get('/dashboard/recommended',headers=self.student);self.assertEqual(r.status_code,200,r.text);first=r.json()[0]
  self.assertEqual(first['id'],1);self.assertEqual(first['score'],75)
  self.assertEqual(first['average_rating'],0);self.assertEqual(first['review_count'],0)
  self.assertTrue(any('curriculum' in reason for reason in first['reasons']))
  self.assertTrue(all(b['score_breakdown']['curriculum']==0 for b in self.client.get('/dashboard/recommended',headers=self.staff).json()))
  self.assertEqual(self.client.get('/dashboard/recommended').status_code,401)
 test_old_accounts_and_optional_signup=None
 test_profile_validation_and_owner_scope=None
