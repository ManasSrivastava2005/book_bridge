import json,subprocess,uuid,httpx
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.book import Book
from app.models.contribution import Contribution,XPTransaction
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 student=User(name='Final student acceptance',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 staff=User(name='Final staff acceptance',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.LIBRARIAN)
 book=Book(title='Paging acceptance guide',author='Fixture',description='Page tables',available_copies=1,total_copies=1)
 db.add_all([student,staff,book]);db.commit();sid=student.id;token=create_access_token(sid,'student');staff_token=create_access_token(staff.id,'librarian')
headers={'Authorization':'Bearer '+token}
r=httpx.put('http://127.0.0.1:8001/academic/personal-curriculum',headers=headers,json={'title':'Acceptance curriculum','subjects':[{'title':'Operating Systems','children':[{'title':'Memory','children':[{'title':'Paging'}]}]}]});assert r.status_code==200,r.text
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/recommendations');
await page.getByRole('heading',{name:'Paging acceptance guide',exact:true}).first().waitFor();
await page.getByText('Catalog metadata matches confirmed topic "Paging". Review the resource for coverage.',{exact:true}).first().waitFor();
await page.goto('http://127.0.0.1:5174/contributions');
await page.getByRole('heading',{name:'Submit and track contributions',exact:true}).waitFor();
if(!page.url().includes('/notes?view=submissions'))throw new Error('Old route did not redirect');
if(await page.getByRole('link',{name:'My Contributions',exact:true}).count())throw new Error('Redundant navigation remains');
await page.getByLabel('Title',{exact:true}).fill('Acceptance OS notes');await page.getByLabel('Subject',{exact:true}).fill('Operating Systems');
await page.getByLabel('File (PDF or UTF-8 text, up to 25 MB)',{exact:true}).setInputFiles({name:'notes.txt',mimeType:'text/plain',buffer:new Uint8Array([80,97,103,105,110,103])});
await page.getByRole('button',{name:'Submit for review',exact:true}).click();await page.getByRole('heading',{name:'Acceptance OS notes',exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/question-banks');await page.getByText('Submit to Library — question papers and banks',{exact:true}).click();
await page.getByLabel('Title',{exact:true}).fill('Acceptance OS paper');await page.getByLabel('Subject',{exact:true}).fill('Operating Systems');await page.getByLabel('Semester',{exact:true}).fill('5');await page.getByLabel('Branch',{exact:true}).fill('CSE');
await page.getByLabel('File (PDF or UTF-8 text, up to 25 MB)',{exact:true}).setInputFiles({name:'paper.txt',mimeType:'text/plain',buffer:new Uint8Array([80,97,103,105,110,103])});
await page.getByRole('button',{name:'Submit for review',exact:true}).click();await page.getByRole('heading',{name:'Acceptance OS paper',exact:true}).waitFor();
if(await page.getByRole('heading',{name:'Acceptance OS notes',exact:true}).count())throw new Error('Notes leaked into paper section');
return {url:page.url(),curriculumRecommendation:true,notesSubmitted:true,paperSubmitted:true,sectionsSeparated:true};
""".replace('TOKEN',json.dumps(token)).replace('Acceptance OS notes','Acceptance OS notes '+str(sid)).replace('Acceptance OS paper','Acceptance OS paper '+str(sid))
def run(program):
 r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55)
 print(r.stdout);print(r.stderr);assert r.returncode==0
run(program)
with fixture.database.SessionLocal() as db:
 rows=db.query(Contribution).filter_by(user_id=sid).all();assert len(rows)==2
 for row in rows:
  payload={'decision':'APPROVED'} if row.kind=='note' else {'decision':'REJECTED','reason':'Please include the examination year.'}
  r=httpx.post(f'http://127.0.0.1:8001/admin/contributions/{row.id}/decision',headers={'Authorization':'Bearer '+staff_token},json=payload);assert r.status_code==200,r.text
run(r"""
await page.getByRole('button',{name:'Refresh submission status',exact:true}).click();await page.getByText('Reason: Please include the examination year.',{exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/notes?view=submissions');await page.getByText('Operating Systems · APPROVED',{exact:true}).waitFor();await page.reload();await page.getByText('Operating Systems · APPROVED',{exact:true}).waitFor();
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));
return {url:page.url(),rejectionReasonVisible:true,approvalPersists:true};
""")
with fixture.database.SessionLocal() as db:
 assert sum(r.amount for r in db.query(XPTransaction).filter_by(user_id=sid))==2
print('Contribution ownership, moderation persistence and exactly 2 XP verified in isolated PostgreSQL.')
