from test_catalog_management import CatalogTests
from app.routers.quizzes import router
from app.models.quiz import Quiz,QuizQuestion

class QuizTests(CatalogTests):
 def setUp(self):super().setUp();self.client.app.include_router(router)
 def payload(self,count=10):return {'title':'Chapter quiz','book_id':1,'chapter':'Processes','permission_confirmed':True,'questions':[{'prompt':f'Question {i}?','options':['A','B','C','D'],'correct_index':1,'explanation':'B is correct.'} for i in range(count)]}
 def test_draft_publish_edit_and_delete(self):
  r=self.client.post('/admin/quizzes',headers=self.staff,json=self.payload());self.assertEqual(r.status_code,201);id=r.json()['id']
  self.assertEqual(len(self.client.get(f'/admin/quizzes/{id}',headers=self.staff).json()['questions']),10)
  self.assertEqual(self.client.patch(f'/admin/quizzes/{id}/state',headers=self.staff,json={'status':'published','active':True}).status_code,200)
  self.assertEqual(self.client.put(f'/admin/quizzes/{id}',headers=self.staff,json=self.payload()).status_code,409)
  self.assertEqual(self.client.delete(f'/admin/quizzes/{id}',headers=self.staff).status_code,409)
  self.client.patch(f'/admin/quizzes/{id}/state',headers=self.staff,json={'status':'draft'})
  self.assertEqual(self.client.put(f'/admin/quizzes/{id}',headers=self.staff,json={**self.payload(),'title':'Edited'}).status_code,200)
  self.assertEqual(self.client.delete(f'/admin/quizzes/{id}',headers=self.staff).status_code,204)
 def test_publication_checks_and_student_cannot_read_answers(self):
  id=self.client.post('/admin/quizzes',headers=self.staff,json=self.payload(9)).json()['id']
  self.assertEqual(self.client.patch(f'/admin/quizzes/{id}/state',headers=self.staff,json={'status':'published','active':True}).status_code,422)
  payload={**self.payload(),'permission_confirmed':False};self.client.put(f'/admin/quizzes/{id}',headers=self.staff,json=payload)
  self.assertEqual(self.client.patch(f'/admin/quizzes/{id}/state',headers=self.staff,json={'status':'published'}).status_code,422)
  payload={**self.payload(),'source_kind':'permitted_material','source_reference':None};self.client.put(f'/admin/quizzes/{id}',headers=self.staff,json=payload)
  self.assertEqual(self.client.patch(f'/admin/quizzes/{id}/state',headers=self.staff,json={'status':'published'}).status_code,422)
  self.assertEqual(self.client.get(f'/admin/quizzes/{id}',headers=self.student).status_code,403)
  self.assertEqual(self.client.post('/admin/quizzes',headers=self.student,json=self.payload()).status_code,403)
 def test_invalid_answers_rejected(self):
  p=self.payload();p['questions'][0]['correct_index']=7
  self.assertEqual(self.client.post('/admin/quizzes',headers=self.staff,json=p).status_code,422)
  p=self.payload();p['questions'][0]['options']=['A','A']
  self.assertEqual(self.client.post('/admin/quizzes',headers=self.staff,json=p).status_code,422)
 test_metadata_persists_and_null_or_unsafe_fields_rejected=None
 test_stock_obligations_and_history_deletion=None
 test_delete_unreferenced_and_student_denied=None
 test_server_pagination_and_filters=None
