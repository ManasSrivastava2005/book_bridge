"""Staff login contract and role tests in an isolated database."""
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.models.library import Library
from app.models.user import User, UserRole
from app.routers import auth, admin
from app.services.auth import hash_password, create_access_token


class StaffAuthTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        with factory() as db:
            for role in UserRole:
                db.add(User(name=role.value, email=f'{role.value}@example.com', role=role,
                            hashed_password=hash_password('isolated-test-password')))
            db.commit()
        def dependency():
            with factory() as db:
                yield db
        app = FastAPI()
        app.include_router(auth.router); app.include_router(admin.router)
        app.dependency_overrides[get_db] = dependency
        self.client = TestClient(app)
        self.factory = factory
        self.addCleanup(engine.dispose); self.addCleanup(self.client.close)

    def test_login_me_and_reuse_token_for_all_roles(self):
        for role in UserRole:
            response = self.client.post('/auth/login', json={'email': f'{role.value}@example.com', 'password': 'isolated-test-password'})
            self.assertEqual(response.status_code, 200)
            headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
            for _ in range(2):
                profile = self.client.get('/auth/me', headers=headers)
                self.assertEqual(profile.status_code, 200)
                self.assertEqual(profile.json()['role'], role.value)
                self.assertNotIn('hashed_password', profile.json())
            expected = 403 if role == UserRole.STUDENT else 200
            self.assertEqual(self.client.get('/admin/dashboard', headers=headers).status_code, expected)

    def test_invalid_password_and_missing_token(self):
        self.assertEqual(self.client.post('/auth/login', json={'email': 'admin@example.com', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 401)
        self.assertEqual(self.client.get('/auth/me').status_code, 401)

    def test_role_is_checked_in_database_not_token_claim(self):
        with self.factory() as db:
            student = db.query(User).filter(User.role == UserRole.STUDENT).one()
            token = create_access_token(student.id, 'admin')
        self.assertEqual(self.client.get('/admin/dashboard', headers={'Authorization': 'Bearer '+token}).status_code, 403)


if __name__ == '__main__': unittest.main()

