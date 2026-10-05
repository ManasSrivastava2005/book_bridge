from test_study import StudyTests
from app.models.study import StudyMember,StudyMessage,StudyAudit
from uuid import uuid4
class ChatUpgradeTests(StudyTests):
 def test_replies_edit_tombstone_membership_and_presence(self):
  rid=self.room();other=self.room('Other')
  self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2))
  parent=self.post(rid).json()['id']
  response=self.client.post(f'/study/rooms/{rid}/messages',headers=self.headers(2),json={'body':'Answer','client_id':str(uuid4()),'reply_to_id':parent})
  self.assertEqual(response.status_code,201,response.text);mid=response.json()['id']
  self.assertEqual(self.client.post(f'/study/rooms/{other}/messages',headers=self.headers(),json={'body':'Wrong room','client_id':str(uuid4()),'reply_to_id':parent}).status_code,422)
  url=f'/study/rooms/{rid}/messages/{mid}'
  self.assertEqual(self.client.patch(url,headers=self.headers(),json={'body':'Owner cannot edit another sender'}).status_code,403)
  self.assertEqual(self.client.patch(url,headers=self.headers(2),json={'body':'Edited answer'}).status_code,200)
  self.assertEqual(self.client.post(f'/study/rooms/{rid}/presence',headers=self.headers(2)).status_code,204)
  people=self.client.get(f'/study/rooms/{rid}/participants',headers=self.headers()).json()['items']
  self.assertTrue(next(p for p in people if p['user_id']==2)['recently_active'])
  self.assertEqual(self.client.get(f'/study/rooms/{rid}/participants',headers=self.headers(3)).status_code,403)
  self.assertEqual(self.client.delete(f'/study/rooms/{rid}/messages/{parent}',headers=self.headers()).status_code,204)
  messages=self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers(2)).json()['items']
  self.assertEqual(messages[0]['body'],'This message was deleted');self.assertEqual(messages[1]['reply']['body'],'This message was deleted');self.assertIsNotNone(messages[1]['edited_at'])
  self.client.post(f'/study/rooms/{rid}/leave',headers=self.headers(2))
  with self.factory() as db:
   membership=db.get(StudyMember,(rid,2));self.assertIsNotNone(membership.left_at);original=membership.joined_at
   self.assertIsNotNone(db.get(StudyMessage,parent).deleted_at)
  self.assertEqual(self.client.post(f'/study/rooms/{rid}/presence',headers=self.headers(2)).status_code,403)
  self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2))
  with self.factory() as db:self.assertEqual(db.get(StudyMember,(rid,2)).joined_at,original);self.assertIsNone(db.get(StudyMember,(rid,2)).left_at)
  self.assertEqual(self.client.get('/study/dashboard/rooms',headers=self.headers(2)).json()['joined_count'],1)
 def test_optional_subject_and_owner_details(self):
  r=self.client.post('/study/rooms',headers=self.headers(),json={'title':'Any topic'});self.assertEqual(r.status_code,201,r.text);rid=r.json()['id']
  payload={'title':'Updated topic','description':'New description'}
  self.assertEqual(self.client.patch(f'/study/rooms/{rid}/details',headers=self.headers(2),json=payload).status_code,403)
  self.assertEqual(self.client.patch(f'/study/rooms/{rid}/details',headers=self.headers(),json=payload).status_code,200)
