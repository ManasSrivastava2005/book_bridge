import json,subprocess,uuid,httpx
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.services.auth import create_access_token
from test_syllabus_processing import text_pdf
with fixture.database.SessionLocal() as db:
 user=User(name='Delete workflow',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 db.add(user);db.commit();token=create_access_token(user.id,'student')
client=httpx.Client(base_url='http://127.0.0.1:8001',headers={'Authorization':'Bearer '+token})
room=client.post('/study/rooms',json={'title':'Delete messages acceptance'}).json()['id']
for i in range(25):
 response=client.post(f'/study/rooms/{room}/messages',json={'body':f'Delete fixture {i}','client_id':str(uuid.uuid4())})
 # Rate-limited chat posting intentionally avoided below for the rest of the fixture.
 if response.status_code!=201:break
# Directly populate isolated test data so acceptance does not depend on post-rate limits.
from app.models.study import StudyMessage
with fixture.database.SessionLocal() as db:
 for j in range(i,25):db.add(StudyMessage(room_id=room,user_id=user.id,body=f'Delete fixture {j}',client_id=str(uuid.uuid4())))
 db.commit()
tree=client.post('/academic/subjects',json={'title':'Delete test subject','semester':3}).json();subject=tree['subjects'][0];sid=subject['id']
pdf=text_pdf(['UNIT 1','Processes','Threads'])
upload=client.post('/academic/syllabi',data={'request_id':str(uuid.uuid4()),'subject_id':sid},files={'file':('confirmed.pdf',pdf,'application/pdf')}).json()
subject['children']=upload['proposal']['subjects'][0]['children']
r=client.post(f'/academic/syllabi/{upload["id"]}/confirm-subject/{sid}',json={'expected_version':tree['expected_version'],'subject':subject});assert r.status_code==200,r.text
pending=client.post('/academic/syllabi',data={'request_id':str(uuid.uuid4()),'subject_id':sid},files={'file':('delete-only.pdf',pdf,'application/pdf')}).json()
program=r"""
await page.setViewportSize({width:1200,height:800});
await page.goto('http://127.0.0.1:5174/login');
await page.evaluate(t=>{localStorage.removeItem('bookbridge_token');sessionStorage.setItem('bookbridge_token',t);},TOKEN);
await page.goto('http://127.0.0.1:5174/study-together/ROOM');
const target=page.locator('article').filter({hasText:'Delete fixture 24'});
await target.getByRole('button',{name:'Delete message',exact:true}).click();
const dialog=target.getByRole('alertdialog',{name:'Delete this message'});
const visible=await dialog.getByRole('button',{name:'Confirm delete',exact:true}).evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=window.innerHeight;});
if(!visible)throw new Error('Delete confirmation still offscreen');
await dialog.getByRole('button',{name:'Cancel delete',exact:true}).click();
await target.getByText('Delete fixture 24',{exact:true}).waitFor();
await target.getByRole('button',{name:'Delete message',exact:true}).click();
await dialog.getByRole('button',{name:'Confirm delete',exact:true}).click();
await page.getByText('This message was deleted',{exact:true}).waitFor();
await page.reload();await page.getByText('This message was deleted',{exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/curriculum');
await page.getByRole('button',{name:'Open Curriculum',exact:true}).click();
await page.getByRole('checkbox',{name:'Processes',exact:true}).waitFor();
const pdfRow=page.getByText('delete-only.pdf · Awaiting review',{exact:true}).locator('..');
await pdfRow.getByRole('button',{name:'Delete PDF',exact:true}).click();
await page.getByRole('button',{name:'Cancel deletion',exact:true}).click();
await pdfRow.getByRole('button',{name:'Delete PDF',exact:true}).click();
await page.getByRole('button',{name:'Confirm deletion',exact:true}).click();
await page.getByText('PDF upload deleted. Confirmed curriculum is unchanged.',{exact:true}).waitFor();
await page.getByRole('checkbox',{name:'Processes',exact:true}).waitFor();
if(await page.getByText('delete-only.pdf · Awaiting review',{exact:true}).count())throw new Error('Deleted PDF still listed');
await page.getByRole('button',{name:'Delete saved curriculum',exact:true}).click();
await page.getByRole('button',{name:'Confirm deletion',exact:true}).click();
await page.getByText('Saved curriculum and associated uploads deleted. You can upload a new syllabus.',{exact:true}).waitFor();
await page.reload();await page.getByRole('button',{name:'Open Curriculum',exact:true}).click();
await page.getByRole('heading',{name:'Delete test subject',exact:true}).waitFor();
if(await page.getByRole('checkbox',{name:'Processes',exact:true}).count())throw new Error('Deleted curriculum still active');
if(await page.getByText('confirmed.pdf · Confirmed',{exact:true}).count())throw new Error('Associated upload still listed');
return {inlineChatConfirmationVisible:visible,chatCancellation:true,chatDeletePersisted:true,pdfCancellation:true,pdfDeletePreservesCurriculum:true,curriculumDeletePersisted:true,subjectPreserved:true};
""".replace('TOKEN',json.dumps(token)).replace('ROOM',str(room))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','55','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=65)
print(r.stdout);print(r.stderr);assert r.returncode==0
assert client.get(f'/academic/syllabi/{upload["id"]}/file').status_code==404
assert client.get(f'/academic/syllabi/{pending["id"]}/file').status_code==404
client.close()
