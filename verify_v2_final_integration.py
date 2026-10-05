"""Final cross-feature integration against the restored PostgreSQL database only."""
import json,uuid,httpx
from pathlib import Path
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.book import Book
from app.models.reservation import Reservation
from app.models.contribution import XPTransaction
from app.services.auth import create_access_token
from test_syllabus_processing import text_pdf
with fixture.database.SessionLocal() as db:
 users=[User(name='Integrated '+role,email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole(role)) for role in ['librarian','student','student']]
 book=Book(title='Integrated paging '+uuid.uuid4().hex[:6],author='Fixture',total_copies=1,available_copies=1)
 db.add_all(users+[book]);db.commit();staff,student,other=[u.id for u in users];bid=book.id;title=book.title
client=httpx.Client(base_url='http://127.0.0.1:8001',timeout=30)
def request(method,path,user=student,expected=200,**kwargs):
 role='librarian' if user==staff else 'student'
 r=client.request(method,path,headers={'Authorization':'Bearer '+create_access_token(user,role)},**kwargs)
 assert r.status_code==expected,(method,path,r.status_code,r.text[:500])
 return r.json() if 'application/json' in r.headers.get('content-type','') else r.content
pdf=text_pdf(['Course: Operating Systems','Unit 1: Memory','Topic: Paging'])
resource=request('POST','/digital-resources/upload',user=staff,expected=201,data={'metadata':json.dumps({'title':'Integrated PDF','author':'Fixture','library_id':None,'is_published':False,'distribution_basis':'permission','rights_evidence':'Original generated test document authorized for this acceptance check.','license_name':'Fixture permission'})},files={'file':('fixture.pdf',pdf,'application/pdf')})
rid=resource['id'];url=resource['file_url']
request('GET',url,expected=404)
request('PATCH',f'/admin/digital-resources/{rid}/lifecycle',user=staff,json={'action':'publish'})
assert request('GET',url)==pdf
request('PATCH',f'/admin/digital-resources/{rid}/lifecycle',user=staff,json={'action':'unpublish'})
request('GET',url,expected=404)
request('PATCH',f'/admin/digital-resources/{rid}/lifecycle',user=staff,json={'action':'publish'})
syllabus=request('POST','/academic/syllabi',expected=201,data={'request_id':str(uuid.uuid4())},files={'file':('syllabus.pdf',pdf,'application/pdf')})
assert request('GET','/academic/curriculum')['curriculum'] is None
request('POST',f"/academic/syllabi/{syllabus['id']}/confirm",json={'title':'Integrated curriculum','subjects':syllabus['proposal']['subjects']})
topic=request('GET','/academic/curriculum')['subjects'][0]['units'][0]['topics'][0]['id']
request('PUT',f'/academic/topics/{topic}/completion?completed=true')
quiz=request('POST','/admin/quizzes',user=staff,expected=201,json={'title':'Integrated quiz','book_id':bid,'chapter':'Paging','permission_confirmed':True,'questions':[{'prompt':f'Question {i}?','options':['A','B'],'correct_index':1,'explanation':'B'} for i in range(10)]})
request('PATCH',f"/admin/quizzes/{quiz['id']}/state",user=staff,json={'status':'published','active':True})
attempt=request('POST',f"/student/quizzes/{quiz['id']}/start");aid=attempt['attempt_id'];assert 'correct_index' not in str(attempt)
for _ in range(2):assert request('POST',f'/student/quizzes/attempts/{aid}/submit',json={'answers':[1]*10})['score']==100
loan=request('POST','/admin/loans',user=staff,expected=201,json={'student_id':other,'book_id':bid,'request_id':str(uuid.uuid4())})
reservation=request('POST','/reservations/',expected=201,json={'book_id':bid});resid=reservation['id'];assert reservation['status']=='pending'
# Leave pending so the browser can verify each staff-driven transition.
Path('v2-integration-fixture.json').write_text(json.dumps({'staff':staff,'student':student,'other':other,'book':bid,'title':title,'initial_loan':loan['id'],'reservation':resid,'syllabus':syllabus['id'],'resource':rid,'quiz':quiz['id']}),encoding='utf-8')
print('Integrated PDF lifecycle, private syllabus confirmation, topic completion, staff quiz and repeat-safe quiz scoring passed; reservation pending for browser verification.')

