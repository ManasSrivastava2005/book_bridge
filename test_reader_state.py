"""Isolated reader API ownership, versioning and validation regressions."""
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.library import Library
from app.models.digital_resource import DigitalResource
from app.models.reader_state import ReaderState
from app.routers.reader import router
from app.services.auth import create_access_token

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory=sessionmaker(bind=self.engine)
        with self.factory() as db:
            for i in range(2):db.add(User(name=f'Reader {i}',email=f'reader{i}@example.com',hashed_password='unused',role=UserRole.STUDENT))
            db.add(DigitalResource(title='PDF',author='Author',resource_type='uploaded_pdf',file_url='/uploads/book.pdf',is_published=True,reviewed_by=1))
            db.add(DigitalResource(title='Draft',author='Author',is_published=False))
            db.commit()
        def get_test_db():
            with self.factory() as db:yield db
        app=FastAPI();app.include_router(router);app.dependency_overrides[get_db]=get_test_db
        self.client=TestClient(app)
        self.addCleanup(self.client.close);self.addCleanup(self.engine.dispose)
        self.headers={'Authorization':'Bearer '+create_access_token(1,'student')}
        self.other={'Authorization':'Bearer '+create_access_token(2,'student')}
        self.value={'version':0,'page':2,'total_pages':3,'document_key':'fixture','theme':'sepia','bookmarks':[{'page':2,'note':'Private note'}],'highlights':[{'id':'abc-123','page':2,'text':'Selected text','note':'My thought','rects':[{'x':0.1,'y':0.2,'width':0.5,'height':0.02}]}]}

    def test_auth_required_and_defaults(self):
        self.assertEqual(self.client.get('/reader/1/state').status_code,401)
        self.assertEqual(self.client.put('/reader/1/state',json=self.value).status_code,401)
        response=self.client.get('/reader/1/state',headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['version'],0)
        with self.factory() as db:self.assertEqual(db.query(ReaderState).count(),0)

    def test_saved_data_survives_new_session_and_is_private(self):
        first=self.client.put('/reader/1/state',headers=self.headers,json=self.value)
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.json()['version'],1)
        self.assertEqual(self.client.get('/reader/1/state',headers=self.headers).json(),first.json())
        self.assertEqual(self.client.get('/reader/1/state',headers=self.other).json()['bookmarks'],[])
        self.assertEqual(self.client.put('/reader/1/state',headers=self.other,json=self.value).status_code,200)
        with self.factory() as db:self.assertEqual(db.query(ReaderState).count(),2)

    def test_stale_browser_cannot_overwrite_newer_notes(self):
        self.client.put('/reader/1/state',headers=self.headers,json=self.value)
        self.assertEqual(self.client.put('/reader/1/state',headers=self.headers,json=self.value).status_code,409)
        new={**self.value,'version':1,'page':3}
        self.assertEqual(self.client.put('/reader/1/state',headers=self.headers,json=new).json()['version'],2)
        self.assertEqual(self.client.put('/reader/1/state',headers=self.headers,json=new).status_code,409)
        self.assertEqual(self.client.get('/reader/1/state',headers=self.headers).json()['page'],3)

    def test_caller_cannot_choose_owner(self):
        self.assertEqual(self.client.put('/reader/1/state',headers=self.headers,json={**self.value,'user_id':2}).status_code,422)

    def test_missing_and_unpublished_resources(self):
        for resource in (2,999):
            self.assertEqual(self.client.get(f'/reader/{resource}/state',headers=self.headers).status_code,404)
            self.assertEqual(self.client.put(f'/reader/{resource}/state',headers=self.headers,json=self.value).status_code,404)

    def test_invalid_pages_and_bounds(self):
        for changes in ({'page':0},{'page':4},{'page':True},{'page':1.5},{'version':-1},{'bookmarks':[{'page':4,'note':''}]},{'bookmarks':[{'page':2,'note':'x'*2001}]},{'theme':'unknown'}):
            with self.subTest(changes=str(changes)[:50]):
                self.assertEqual(self.client.put('/reader/1/state',headers=self.headers,json={**self.value,**changes}).status_code,422)

    def test_invalid_duplicate_highlights_and_geometry(self):
        mark=self.value['highlights'][0]
        for marks in ([mark,mark],[{**mark,'rects':[{'x':.9,'y':0,'width':.5,'height':.1}]}],[{**mark,'rects':[]}],[{**mark,'text':''}]):
            self.assertEqual(self.client.put('/reader/1/state',headers=self.headers,json={**self.value,'highlights':marks}).status_code,422)

    def test_remove_bookmark_and_highlight(self):
        self.client.put('/reader/1/state',headers=self.headers,json=self.value)
        response=self.client.put('/reader/1/state',headers=self.headers,json={**self.value,'version':1,'bookmarks':[],'highlights':[]})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['highlights'],[])

    def test_additive_migration_is_repeatable_and_preserves_rows(self):
        ReaderState.__table__.create(self.engine,checkfirst=True)
        ReaderState.__table__.create(self.engine,checkfirst=True)
        with self.factory() as db:
            self.assertEqual(db.query(User).count(),2)
            self.assertEqual(db.query(DigitalResource).count(),2)

if __name__=='__main__':unittest.main()
