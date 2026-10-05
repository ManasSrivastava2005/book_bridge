from datetime import date,timedelta
from test_personal_curriculum import PersonalCurriculumTests
from app.models.book import Book
from app.models.user import User
from app.models.digital_resource import DigitalResource
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.student_exam import StudentExam
from app.models.quiz import Quiz
from app.services.student_curriculum import curriculum_data
from app.services.recommendations import recommendations
from app.services.academic_plan import generate_plan

class PersonalRecommendationTests(PersonalCurriculumTests):
 def test_confirmed_metadata_matches_and_safe_quiz_mapping(self):
  tree=self.save().json();subject=tree['subjects'][0];topic=subject['children'][0]['children'][0]
  with self.factory() as db:
   book=Book(title='Paging guide',author='Author',description='Page tables and TLB',available_copies=1,total_copies=1);db.add(book)
   db.add(DigitalResource(title='Paging private',author='Author',is_published=True,reviewed_by=None))
   db.add(StudentExam(user_id=2,subject_id=subject['id'],name='Exam',exam_type='Midterm',date=date.today()+timedelta(days=3),topic_ids=[topic['id']]))
   shared=Curriculum(family='shared-quiz',title='Shared',college='C',program='P',branch='CS',semester=1);db.add(shared);db.flush()
   shared_subject=CurriculumNode(curriculum_id=shared.id,kind='subject',title='Operating Systems');db.add(shared_subject);db.flush()
   unit=CurriculumNode(curriculum_id=shared.id,parent_id=shared_subject.id,kind='unit',title='Memory');db.add(unit);db.flush()
   shared_topic=CurriculumNode(curriculum_id=shared.id,parent_id=unit.id,kind='topic',title='Paging');db.add(shared_topic);db.flush()
   quiz=Quiz(title='Paging quiz',subject_id=shared_subject.id,topic_id=shared_topic.id,status='published',active=True,permission_confirmed=True,created_by=1);db.add(quiz);db.commit();bid=book.id;qid=quiz.id
   resources=curriculum_data(db,2)['subjects'][0]['units'][0]['topics'][0]['resources']
   self.assertTrue(any(r['id']==bid and r['kind']=='book' for r in resources))
   self.assertFalse(any(r['kind']=='digital_resource' for r in resources))
   result=next(r for r in recommendations(db,db.get(User,2)) if r['id']==bid)
   self.assertEqual(result['score_breakdown']['curriculum'],40);self.assertGreater(result['score_breakdown']['exam'],0)
   self.assertIn('metadata matches',result['reasons'][0])
   plan=generate_plan(db,2);self.assertTrue(any(t['quiz_id']==qid for t in plan['tasks']));db.commit()
  topic['title']='Concurrency'
  self.assertEqual(self.save(tree).status_code,200)
  with self.factory() as db:
   result=next(r for r in recommendations(db,db.get(User,2)) if r['id']==bid)
   self.assertEqual(result['score_breakdown']['curriculum'],0)
   self.assertFalse(any(t['quiz_id']==qid for t in generate_plan(db,2)['tasks']))
