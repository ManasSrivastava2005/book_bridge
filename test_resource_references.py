"""Protect curriculum references using enforced foreign keys in an isolated database."""
from test_catalog_management import CatalogTests
from app.models.curriculum import Curriculum, CurriculumNode, CurriculumResource
from app.models.contribution import Contribution
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.digital_resource import DigitalResource
from app.routers import notes, question_banks, digital_resources

class ResourceReferenceTests(CatalogTests):
 def test_referenced_resources_return_conflict_and_keep_records(self):
  with self.engine.connect() as connection:
   connection.exec_driver_sql('PRAGMA foreign_keys=ON')
  for router in (notes.router,question_banks.router,digital_resources.router):self.client.app.include_router(router)
  with self.factory() as db:
   curriculum=Curriculum(family='fixture',title='CS',college='Test',program='CS',branch='CS',semester=1)
   db.add(curriculum);db.flush()
   topic=CurriculumNode(curriculum_id=curriculum.id,kind='topic',title='Memory');db.add(topic);db.flush()
   resources=[Note(title='Notes',subject='OS',user_id=1,status='published'),QuestionBank(title='Paper',subject='OS',semester=1,branch='CS'),DigitalResource(title='Ebook',author='Author')]
   for resource in resources:db.add(resource)
   db.flush()
   for field,resource in zip(('note_id','question_bank_id','digital_resource_id'),resources):db.add(CurriculumResource(topic_id=topic.id,**{field:resource.id}))
   db.commit()
  for route,model in zip(('notes','question-banks','digital-resources'),(Note,QuestionBank,DigitalResource)):
   response=self.client.delete(f'/{route}/1',headers=self.staff)
   self.assertEqual(response.status_code,409,response.text)
   with self.factory() as db:self.assertIsNotNone(db.get(model,1))
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
