import json,subprocess,uuid,httpx
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 user=User(name='Subject deletion acceptance',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 db.add(user);db.commit();token=create_access_token(user.id,'student')
with httpx.Client(base_url='http://127.0.0.1:8001',headers={'Authorization':'Bearer '+token}) as client:
 for title in ['Temporary subject','Keep this subject']:
  r=client.post('/academic/subjects',json={'title':title,'semester':5});assert r.status_code==201,r.text
program=r"""
await page.setViewportSize({width:1200,height:900});
await page.goto('http://127.0.0.1:5174/login');
await page.evaluate(t=>{localStorage.removeItem('bookbridge_token');sessionStorage.setItem('bookbridge_token',t);},TOKEN);
await page.goto('http://127.0.0.1:5174/curriculum');
const card=page.locator('article').filter({hasText:'Temporary subject'});
await card.getByRole('button',{name:'Delete subject',exact:true}).click();
await card.getByRole('button',{name:'Cancel',exact:true}).click();
await card.getByRole('heading',{name:'Temporary subject',exact:true}).waitFor();
await card.getByRole('button',{name:'Delete subject',exact:true}).click();
await card.getByRole('button',{name:'Confirm delete subject',exact:true}).click();
await page.getByText('1 subjects',{exact:true}).waitFor();
if(await page.getByRole('heading',{name:'Temporary subject',exact:true}).count())throw new Error('Subject still visible');
await page.reload();
await page.getByRole('heading',{name:'Keep this subject',exact:true}).waitFor();
if(await page.getByRole('heading',{name:'Temporary subject',exact:true}).count())throw new Error('Deleted subject returned');
await page.getByRole('button',{name:'Open Curriculum',exact:true}).click();
await page.getByRole('button',{name:'Edit saved curriculum',exact:true}).waitFor();
await page.getByRole('button',{name:'Delete saved curriculum',exact:true}).waitFor();
await page.getByRole('button',{name:'All semester 5 subjects',exact:true}).click();
await page.getByRole('button',{name:'Delete subject',exact:true}).click();
await page.getByRole('button',{name:'Confirm delete subject',exact:true}).click();
await page.getByRole('heading',{name:'Start with your first subject',exact:true}).waitFor();
return {cancelPreservedSubject:true,deleteRemovedCard:true,reloadPersisted:true,siblingPreserved:true,existingCurriculumControlsPreserved:true,lastSubjectEmptyState:true};
""".replace('TOKEN',json.dumps(token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55)
print(r.stdout);print(r.stderr);assert r.returncode==0
