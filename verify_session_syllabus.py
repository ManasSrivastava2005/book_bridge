import json,subprocess,uuid,httpx
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.syllabus_upload import SyllabusUpload
from app.models.curriculum import CurriculumNode
from app.services.auth import create_access_token
from test_syllabus_processing import text_pdf
with fixture.database.SessionLocal() as db:
 student=User(name='Syllabus acceptance',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 db.add(student);db.commit();sid=student.id;token=create_access_token(sid,'student');staff=db.query(User).filter_by(role=UserRole.LIBRARIAN).first();staff_token=create_access_token(staff.id,'librarian')
pdf=text_pdf(['Course: Operating Systems','Course code: CS301','Unit 1: Memory','Topic: Paging','Objectives: Explain page tables','Subtopics: TLB; frames','Review this unassigned paragraph'])
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>sessionStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/curriculum');
await page.getByRole('heading',{name:'My Curriculum',exact:true}).waitFor();
await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),STAFF_TOKEN);
await page.getByLabel('Syllabus PDF',{exact:true}).setInputFiles({name:'OS-syllabus.pdf',mimeType:'application/pdf',buffer:new Uint8Array(BYTES)});
await page.getByRole('button',{name:'Upload and extract syllabus',exact:true}).click();
await page.getByText('PDF extracted privately. Review every detected section before confirming.',{exact:true}).waitFor();
const before=await page.evaluate(async token=>{const r=await fetch('http://127.0.0.1:8001/academic/curriculum',{headers:{Authorization:'Bearer '+token}});return (await r.json()).curriculum;},TOKEN);
if(before!==null)throw new Error('Upload changed curriculum before confirmation');
await page.getByText('Detected headings and page references',{exact:true}).click();
await page.getByText('Unassigned text to review (1 lines)',{exact:true}).click();
await page.getByText('Page 1, line 7: Review this unassigned paragraph',{exact:true}).waitFor();
await page.getByLabel('Topic title',{exact:true}).fill('Virtual memory paging');
await page.getByRole('button',{name:'Confirm reviewed syllabus',exact:true}).click();
await page.getByText('Syllabus confirmed. Your personal curriculum is now active.',{exact:true}).waitFor();
await page.reload();
await page.getByRole('checkbox',{name:'Virtual memory paging',exact:true}).waitFor();
await page.getByText('OS-syllabus.pdf · Confirmed',{exact:true}).waitFor();
await page.evaluate(()=>{sessionStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_token');});
return {url:page.url(),uploadDidNotActivate:true,pageEvidence:true,unassignedTextVisible:true,editedConfirmationPersisted:true};
""".replace('STAFF_TOKEN',json.dumps(staff_token)).replace('TOKEN',json.dumps(token)).replace('BYTES',json.dumps(list(pdf)))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55)
print(r.stdout);print(r.stderr);assert r.returncode==0
with fixture.database.SessionLocal() as db:
 row=db.query(SyllabusUpload).filter_by(user_id=sid).one();assert row.state=='confirmed'
 assert db.query(CurriculumNode).filter_by(curriculum_id=row.curriculum_id,kind='topic').one().title=='Virtual memory paging'
 response=httpx.get(f'http://127.0.0.1:8001/academic/syllabi/{row.id}/file',headers={'Authorization':'Bearer '+token});assert response.content==pdf
 assert httpx.get(f'http://127.0.0.1:8001/academic/syllabi/{row.id}/file').status_code==401
print('Confirmed curriculum and authenticated original PDF verified.')
