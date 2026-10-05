"""Isolated Study Together tests: no live records or messages are used."""
import unittest
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.models.library import Library
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.models.study import StudyRoom, StudyMember, StudyMessage
from app.routers import study
from app.services.auth import create_access_token
from migrate_study import migrate


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        @event.listens_for(self.engine,'connect')
        def foreign_keys(connection,_): connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine,tables=[Library.__table__,User.__table__,Notification.__table__])
        migrate(self.engine)
        self.factory=sessionmaker(bind=self.engine)
        with self.factory() as db:
            for i,role in enumerate([UserRole.STUDENT,UserRole.STUDENT,UserRole.STUDENT,UserRole.LIBRARIAN]):
                db.add(User(id=i+1,name=f'Study user {i+1}',email=f'study{i}@example.test',hashed_password='unused',role=role))
            db.commit()
        def dependency():
            with self.factory() as db: yield db
        app=FastAPI();app.include_router(study.router);app.dependency_overrides[get_db]=dependency
        self.client=TestClient(app)
        self.addCleanup(self.client.close);self.addCleanup(self.engine.dispose)

    def headers(self,user=1):
        return {'Authorization':'Bearer '+create_access_token(user,'librarian' if user==4 else 'student')}

    def room(self,title='Operating Systems'):
        response=self.client.post('/study/rooms',headers=self.headers(),json={'title':title,'subject':'CS','description':'Review process scheduling'})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()['id']

    def post(self,room,user=1,body='How does scheduling work?',client_id=None):
        return self.client.post(f'/study/rooms/{room}/messages',headers=self.headers(user),json={'body':body,'client_id':client_id or str(uuid4())})

    def test_auth_and_owner_assignment(self):
        self.assertEqual(self.client.get('/study/rooms').status_code,401)
        self.assertEqual(self.client.post('/study/rooms',json={'title':'Room','subject':'CS'}).status_code,401)
        rid=self.room()
        room=self.client.get(f'/study/rooms/{rid}',headers=self.headers()).json()
        self.assertEqual(room['owner_id'],1);self.assertTrue(room['is_member']);self.assertEqual(room['member_count'],1)
        self.assertEqual(self.client.post('/study/rooms',headers=self.headers(),json={'title':'Room','subject':'CS','owner_id':2}).status_code,422)
        for path in [f'/study/rooms/{rid}',f'/study/rooms/{rid}/messages']:
            self.assertEqual(self.client.get(path).status_code,401)

    def test_membership_and_discussion_isolation(self):
        rid=self.room();other=self.room('Other')
        self.assertEqual(self.post(rid,2).status_code,403)
        self.assertEqual(self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers(2)).status_code,403)
        for _ in range(2):
            response=self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2))
            self.assertEqual(response.status_code,200);self.assertEqual(response.json()['member_count'],2)
        posted=self.post(rid,2,body='<script>alert(1)</script>')
        self.assertEqual(posted.status_code,201)
        messages=self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers()).json()['items']
        self.assertEqual(messages[0]['body'],'<script>alert(1)</script>')
        self.assertNotIn('email',messages[0]);self.assertNotIn('client_id',messages[0])
        self.assertEqual(self.client.get(f'/study/rooms/{other}/messages',headers=self.headers()).json()['items'],[])
        self.assertEqual(self.client.post(f'/study/rooms/{rid}/leave',headers=self.headers(2)).status_code,204)
        self.assertEqual(self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers(2)).status_code,403)
        self.assertEqual(self.client.post(f'/study/rooms/{rid}/leave',headers=self.headers()).status_code,409)

    def test_retry_safe_post_and_payload_validation(self):
        rid=self.room();key=str(uuid4())
        first=self.post(rid,client_id=key);second=self.post(rid,client_id=key)
        self.assertEqual(first.json(),second.json())
        self.assertEqual(self.post(rid,body='Changed body',client_id=key).status_code,409)
        for body in ['   ','x'*4001]: self.assertEqual(self.post(rid,body=body).status_code,422)
        self.assertEqual(self.post(rid,client_id='not-uuid').status_code,422)
        for fields in [{'title':' ','subject':'CS'},{'title':'x'*121,'subject':'CS'},{'title':'Room','subject':'x'*101}]:
            self.assertEqual(self.client.post('/study/rooms',headers=self.headers(),json=fields).status_code,422)
        with self.factory() as db:self.assertEqual(db.query(StudyMessage).count(),1)

    def test_archive_reopen_and_moderation(self):
        rid=self.room();self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2))
        message=self.post(rid,2).json()['id']
        self.assertEqual(self.client.delete(f'/study/rooms/{rid}/messages/{message}',headers=self.headers(3)).status_code,403)
        self.assertEqual(self.client.patch(f'/study/rooms/{rid}',headers=self.headers(2),json={'archived':True}).status_code,403)
        self.assertEqual(self.client.patch(f'/study/rooms/{rid}',headers=self.headers(),json={'archived':True}).status_code,200)
        self.assertEqual(self.post(rid).status_code,409)
        self.assertEqual(self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(3)).status_code,409)
        self.assertEqual(self.client.get('/study/rooms',headers=self.headers()).json()['items'],[])
        self.assertEqual(len(self.client.get('/study/rooms?mine=true',headers=self.headers()).json()['items']),1)
        self.assertEqual(self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers(2)).status_code,200)
        self.assertEqual(self.client.get(f'/study/rooms/{rid}/messages',headers=self.headers(4)).status_code,200)
        self.assertEqual(self.client.delete(f'/study/rooms/{rid}/messages/{message}',headers=self.headers()).status_code,204)
        self.assertEqual(self.client.patch(f'/study/rooms/{rid}',headers=self.headers(4),json={'archived':False}).status_code,200)
        self.assertEqual(self.post(rid).status_code,201)

    def test_room_scoped_delete_and_own_message_delete_after_leaving(self):
        rid=self.room();other=self.room('Other')
        self.client.post(f'/study/rooms/{rid}/join',headers=self.headers(2))
        message=self.post(rid,2).json()['id']
        self.assertEqual(self.client.delete(f'/study/rooms/{other}/messages/{message}',headers=self.headers()).status_code,404)
        self.client.post(f'/study/rooms/{rid}/leave',headers=self.headers(2))
        self.assertEqual(self.client.delete(f'/study/rooms/{rid}/messages/{message}',headers=self.headers(2)).status_code,204)

    def test_pagination_search_and_missing_room(self):
        ids=[self.room(title) for title in ['Alpha','Beta','Gamma']]
        page=self.client.get('/study/rooms?limit=2',headers=self.headers()).json()
        self.assertEqual([r['id'] for r in page['items']],list(reversed(ids))[0:2])
        last=self.client.get('/study/rooms',params={'before':page['next_before'],'limit':2},headers=self.headers()).json()
        self.assertEqual([r['id'] for r in last['items']],[ids[0]]);self.assertIsNone(last['next_before'])
        self.assertEqual(len(self.client.get('/study/rooms?search=alpha',headers=self.headers()).json()['items']),1)
        rid=ids[0]
        messages=[self.post(rid,body=str(i)).json()['id'] for i in range(4)]
        page=self.client.get(f'/study/rooms/{rid}/messages?limit=2',headers=self.headers()).json()
        self.assertEqual([m['id'] for m in page['items']],messages[2:])
        older=self.client.get(f'/study/rooms/{rid}/messages',params={'limit':2,'before':page['next_before']},headers=self.headers()).json()
        self.assertEqual([m['id'] for m in older['items']],messages[:2])
        self.assertEqual(self.client.get('/study/rooms/999',headers=self.headers()).status_code,404)
        self.assertEqual(self.client.get('/study/rooms?limit=51',headers=self.headers()).status_code,422)
        self.assertEqual(self.client.get(f'/study/rooms/{rid}/messages?limit=101',headers=self.headers()).status_code,422)

    def test_migration_is_idempotent_and_preserves_existing_rows(self):
        rid=self.room();self.post(rid)
        migrate(self.engine);migrate(self.engine)
        self.assertTrue({'study_rooms','study_members','study_messages'} <= set(inspect(self.engine).get_table_names()))
        with self.factory() as db:
            self.assertEqual(db.query(User).count(),4)
            self.assertEqual(db.query(StudyRoom).count(),1)
            self.assertEqual(db.query(StudyMember).count(),1)
            self.assertEqual(db.query(StudyMessage).count(),1)


if __name__=='__main__': unittest.main()
