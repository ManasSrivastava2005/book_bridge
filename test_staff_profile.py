import unittest
from unittest.mock import patch
from app.routers import staff_profile, academic, student_exams, academic_plan, users
from app.models.user import User, UserRole
from app.services.auth import create_access_token
from app.models.contribution import XPTransaction
from test_staff_auth import StaffAuthTests

class StaffProfileTests(StaffAuthTests):
    def setUp(self):
        super().setUp()
        for module in (staff_profile, academic, student_exams, academic_plan, users):
            self.client.app.include_router(module.router)
        with self.factory() as db:
            self.headers = {u.role.value: {'Authorization': 'Bearer '+create_access_token(u.id,u.role.value)} for u in db.query(User)}

    def test_portal_mismatch_denied_before_rewards(self):
        for role,portal in [('student','staff'),('librarian','student'),('admin','student')]:
            r=self.client.post('/auth/login',json={'email':role+'@example.com','password':'isolated-test-password','portal':portal})
            self.assertEqual(r.status_code,403)
        with self.factory() as db:self.assertEqual(db.query(XPTransaction).count(),0)
        for role,portal in [('student','student'),('librarian','staff'),('admin','staff')]:
            self.assertEqual(self.client.post('/auth/login',json={'email':role+'@example.com','password':'isolated-test-password','portal':portal}).status_code,200)

    def test_staff_profile_allowlist_and_persistence(self):
        self.assertEqual(self.client.get('/admin/profile').status_code,401)
        self.assertEqual(self.client.get('/admin/profile',headers=self.headers['student']).status_code,403)
        for role in ('librarian','admin'):
            h=self.headers[role]
            r=self.client.patch('/admin/profile',headers=h,json={'name':'Updated staff'})
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(self.client.get('/admin/profile',headers=h).json()['name'],'Updated staff')
            self.assertEqual(set(r.json()),{'name','email','role','profile_image','library'})
            for key,value in [('role','admin'),('library_id',42),('semester',4),('profile_image','javascript:bad')]:
                self.assertEqual(self.client.patch('/admin/profile',headers=h,json={'name':'staff',key:value}).status_code,422)
            self.assertEqual(self.client.patch('/admin/profile',headers=h,json={'name':'  '}).status_code,422)

    def test_staff_cannot_use_student_academic_routes(self):
        for role in ('librarian','admin'):
            for route in ('/academic/profile','/academic/curriculum','/academic/learning-path','/academic/exams','/academic/plan'):
                self.assertEqual(self.client.get(route,headers=self.headers[role]).status_code,403,route)
            for route in ('/auth/profile','/users/me'):
                self.assertEqual(self.client.put(route,headers=self.headers[role],json={'semester':5}).status_code,403)

    def test_invalid_identity_and_expired_session(self):
        with patch('app.dependencies.decode_access_token',return_value={'sub':'not-an-integer'}):
            self.assertEqual(self.client.get('/admin/profile',headers=self.headers['librarian']).status_code,401)
        with patch('app.dependencies.decode_access_token',return_value=None):
            self.assertEqual(self.client.get('/admin/profile',headers=self.headers['librarian']).status_code,401)

if __name__=='__main__':unittest.main()
