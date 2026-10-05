import json,subprocess,uuid
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.topic_progress import TopicProgress
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 student=User(name='Personal curriculum fixture',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 db.add(student);db.commit();sid=student.id;token=create_access_token(sid,'student')
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/curriculum');
await page.getByRole('button',{name:'Create or edit personal curriculum',exact:true}).click();
await page.getByLabel('Curriculum title',{exact:true}).fill('My verified CS curriculum');
await page.getByRole('button',{name:'Add subject',exact:true}).click();
await page.getByLabel('Subject title',{exact:true}).fill('Operating Systems');
await page.getByLabel('Course code',{exact:true}).fill('CS301');
await page.getByRole('button',{name:'Add unit',exact:true}).click();
await page.getByLabel('Unit title',{exact:true}).fill('Memory management');
await page.getByRole('button',{name:'Add topic',exact:true}).click();
await page.getByLabel('Topic title',{exact:true}).fill('Paging');
await page.getByLabel('Topic objectives',{exact:true}).fill('Explain address translation.');
await page.getByLabel('Subtopics (one per line)',{exact:true}).fill('Page tables\nTLB');
await page.getByRole('button',{name:'Confirm curriculum',exact:true}).click();
await page.getByText('Personal curriculum confirmed. Learning Path and Academic Plan now use these subjects.',{exact:true}).waitFor();
const completion=page.waitForResponse(r=>r.url().includes('/completion') && r.request().method()==='PUT');await page.getByRole('checkbox',{name:'Paging',exact:true}).click();const completionResponse=await completion;if(completionResponse.status()!==200)throw new Error('Topic completion failed');
await page.reload();
await page.getByRole('checkbox',{name:'Paging',exact:true}).waitFor();
const completed=await page.getByRole('checkbox',{name:'Paging',exact:true}).isChecked();
await page.getByRole('button',{name:'Create or edit personal curriculum',exact:true}).click();
await page.getByLabel('Topic title',{exact:true}).fill('Virtual memory paging');
await page.getByRole('button',{name:'Confirm curriculum',exact:true}).click();
await page.getByRole('checkbox',{name:'Virtual memory paging',exact:true}).waitFor();
const preserved=await page.getByRole('checkbox',{name:'Virtual memory paging',exact:true}).isChecked();
await page.evaluate(()=>window.confirm=()=>true);
await page.getByLabel('Curriculum semester',{exact:true}).selectOption('2');
await page.getByLabel('Curriculum title',{exact:true}).fill('Second semester');
await page.getByRole('button',{name:'Add subject',exact:true}).click();await page.getByLabel('Subject title',{exact:true}).fill('Data Structures');
await page.getByRole('button',{name:'Confirm curriculum',exact:true}).click();await page.getByRole('button',{name:'Use semester 2',exact:true}).waitFor();
await page.getByLabel('Curriculum semester',{exact:true}).selectOption('1');await page.getByLabel('Topic title',{exact:true}).waitFor();
await page.getByRole('button',{name:'Use semester 1',exact:true}).click();await page.getByText('Semester 1 is now active.',{exact:true}).waitFor();
await page.reload();if(!await page.getByRole('checkbox',{name:'Virtual memory paging',exact:true}).isChecked())throw new Error('Semester progress lost');
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));
return {url:page.url(),manualTree:true,reloadProgress:completed,editPreservesProgress:preserved};
""".replace('TOKEN',json.dumps(token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55)
print(r.stdout);print(r.stderr);assert r.returncode==0
with fixture.database.SessionLocal() as db:
 curriculum=db.query(Curriculum).filter_by(owner_user_id=sid,semester=1).one()
 topic=db.query(CurriculumNode).filter_by(curriculum_id=curriculum.id,kind='topic').one()
 assert topic.title=='Virtual memory paging' and db.get(TopicProgress,(sid,topic.id))
print('Stable topic ID and completed progress verified in isolated database.')
