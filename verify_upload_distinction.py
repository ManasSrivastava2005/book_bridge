import json,subprocess,uuid,httpx
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.note import Note
from app.models.contribution import Contribution,XPTransaction
from app.models.question_bank import QuestionBank
from app.models.notification import Notification
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 student=User(name='Upload distinction check',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT);db.add(student);db.commit();sid=student.id;token=create_access_token(sid,'student');staff=db.query(User).filter_by(role=UserRole.LIBRARIAN).first();staff_token=create_access_token(staff.id,'librarian')
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5174/notes');await page.getByRole('button',{name:'Upload Private Note',exact:true}).click();
await page.locator('#note-title').fill('Private study draft');await page.locator('#note-subject').fill('Operating Systems');await page.locator('#note-file').setInputFiles({name:'private.txt',mimeType:'text/plain',buffer:new Uint8Array([80,114,105,118,97,116,101])});await page.getByRole('button',{name:'Upload private note',exact:true}).click();await page.getByText('Your private note was uploaded successfully.',{exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/question-banks');await page.getByText('Submit to Library — question papers and banks',{exact:true}).click();await page.locator('details select').selectOption('question_bank');await page.getByLabel('Title',{exact:true}).fill('Question bank acceptance '+SID);await page.getByLabel('Subject',{exact:true}).fill('Operating Systems');await page.getByLabel('Semester',{exact:true}).fill('5');await page.getByLabel('Branch',{exact:true}).fill('CSE');await page.getByLabel('File (PDF or UTF-8 text, up to 25 MB)',{exact:true}).setInputFiles({name:'bank.txt',mimeType:'text/plain',buffer:new Uint8Array([81,117,101,115,116,105,111,110,115])});await page.getByRole('button',{name:'Submit for review',exact:true}).click();await page.getByRole('heading',{name:'Question bank acceptance '+SID,exact:true}).waitFor();await page.getByText('Operating Systems · PENDING',{exact:true}).waitFor();await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));return {url:page.url(),privateNoteUploaded:true,questionBankPending:true};
""".replace('TOKEN',json.dumps(token)).replace('SID',str(sid))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','40','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=50);print(r.stdout);print(r.stderr);assert r.returncode==0
client=httpx.Client(base_url='http://127.0.0.1:8001');sh={'Authorization':'Bearer '+staff_token};h={'Authorization':'Bearer '+token}
with fixture.database.SessionLocal() as db:
 private=db.query(Note).filter_by(user_id=sid,status='personal').one();assert client.get(private.file_url,headers=h).status_code==200;assert client.get(private.file_url,headers=sh).status_code==404
 submission=db.query(Contribution).filter_by(user_id=sid).one();assert submission.kind=='question_bank';cid=submission.id
assert any(r['id']==cid for r in client.get('/admin/contributions',headers=sh,params={'search':'Question bank acceptance '+str(sid)}).json()['items'])
assert client.get(f'/admin/contributions/{cid}/file',headers=sh).content==b'Questions'
for _ in range(2):assert client.post(f'/admin/contributions/{cid}/decision',headers=sh,json={'decision':'APPROVED'}).status_code==200
with fixture.database.SessionLocal() as db:
 contribution=db.get(Contribution,cid);bank=db.get(QuestionBank,contribution.question_bank_id);assert bank and client.get(bank.file_url).content==b'Questions'
 assert sum(r.amount for r in db.query(XPTransaction).filter_by(user_id=sid,event_type='CONTRIBUTION'))==2
 assert db.query(Notification).filter_by(user_id=sid).count()>=1
 assert db.query(Contribution).filter_by(user_id=sid).count()==1
print('Private note stayed private and created no moderation item. Public question bank reached queue, previewed, published and downloaded; notification exists; repeated approval awarded exactly 2 XP.')

