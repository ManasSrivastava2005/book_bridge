"""Real browser acceptance against the isolated database; no working-account writes."""
import json,subprocess,uuid
from datetime import date,timedelta
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.services.auth import create_access_token
from test_syllabus_processing import text_pdf

with fixture.database.SessionLocal() as db:
 student=User(name='Curriculum acceptance',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 db.add(student);db.commit();token=create_access_token(student.id,'student')
pdf=text_pdf(['UNIT 1','Processes','Threads','UNIT 2','CPU Scheduling','Scheduling Algorithms','Subtopics: Round Robin; FCFS'])
program=r"""
await page.setViewportSize({width:1440,height:1000});
await page.goto('http://127.0.0.1:5174/login');
await page.evaluate(t=>{localStorage.removeItem('bookbridge_token');sessionStorage.setItem('bookbridge_token',t);},TOKEN);
await page.goto('http://127.0.0.1:5174/curriculum');
await page.getByRole('heading',{name:'My Curriculum',exact:true}).waitFor();
await page.getByRole('button',{name:'Add Subject',exact:true}).click();
await page.getByLabel('Subject Name',{exact:true}).fill('Operating Systems');
await page.getByLabel('Semester',{exact:true}).fill('3');
await page.getByLabel('Subject Code (optional)',{exact:true}).fill('CSE2004');
await page.getByRole('button',{name:'Create subject',exact:true}).click();
await page.getByRole('heading',{name:'Operating Systems',exact:true}).waitFor();
await page.getByRole('button',{name:'+ Add exam',exact:true}).click();
await page.getByLabel('Exam name',{exact:true}).fill('CAT-II');
await page.getByLabel('Exam date',{exact:true}).fill(EXAM_DATE);
await page.getByRole('button',{name:'Save exam',exact:true}).click();
await page.getByRole('button',{name:'Edit CAT-II',exact:true}).waitFor();
await page.getByLabel('Syllabus PDF',{exact:true}).setInputFiles({name:'OS-syllabus.pdf',mimeType:'application/pdf',buffer:new Uint8Array(BYTES)});
await page.getByRole('button',{name:'Upload and extract syllabus',exact:true}).click();
await page.getByRole('heading',{name:'Review Your Curriculum',exact:true}).waitFor();
const before=await page.evaluate(async token=>{const r=await fetch('http://127.0.0.1:8001/academic/workspace?semester=3',{headers:{Authorization:'Bearer '+token}});return (await r.json()).subjects[0].total_topics;},TOKEN);
if(before!==0)throw new Error('Unconfirmed syllabus became active');
await page.getByLabel('Topic title',{exact:true}).nth(0).fill('Process management');
await page.getByRole('button',{name:'Confirm Curriculum',exact:true}).click();
await page.getByRole('checkbox',{name:'Process management',exact:true}).waitFor();
await page.getByRole('button',{name:'Edit CAT-II',exact:true}).click();
await page.getByRole('checkbox',{name:'Include CPU Scheduling',exact:true}).check();
await page.getByRole('button',{name:'Save exam',exact:true}).click();
await page.getByText('Included in CAT-II',{exact:true}).waitFor();
await page.getByLabel('Study time (minutes/day)',{exact:true}).fill('30');
await page.getByRole('button',{name:'Save study time',exact:true}).click();
await page.getByText('Exam-covered topics first · 30 minutes/day across all subjects.',{exact:true}).waitFor();
const path=await page.evaluate(async token=>{const r=await fetch('http://127.0.0.1:8001/academic/learning-path',{headers:{Authorization:'Bearer '+token}});return await r.json();},TOKEN);
if(path.steps[0].title!=='CPU Scheduling'||path.daily_minutes!==30)throw new Error('Exam priority or study budget incorrect');
await page.getByRole('checkbox',{name:'CPU Scheduling',exact:true}).click();
await page.getByText('1 of 4 topics completed · 25%',{exact:true}).waitFor();
await page.screenshot({path:'curriculum-subject-desktop.png',fullPage:true});
await page.getByRole('button',{name:'Add Subject',exact:true}).click();
await page.getByLabel('Subject Name',{exact:true}).fill('Data Structures');
await page.getByRole('button',{name:'Create subject',exact:true}).click();
await page.getByRole('heading',{name:'Data Structures',exact:true}).waitFor();
await page.getByRole('button',{name:'All semester 3 subjects',exact:true}).click();
await page.getByText('2 subjects',{exact:true}).waitFor();
await page.screenshot({path:'curriculum-cards-desktop.png',fullPage:true});
if(await page.getByRole('link',{name:'My Academic Plan',exact:true}).count())throw new Error('Retired navigation remains');
await page.getByRole('button',{name:'Add Subject',exact:true}).click();
await page.getByLabel('Subject Name',{exact:true}).fill('Mathematics');
await page.getByLabel('Semester',{exact:true}).fill('4');
await page.getByRole('button',{name:'Create subject',exact:true}).click();
await page.getByRole('heading',{name:'Mathematics',exact:true}).waitFor();
await page.getByLabel('Current semester',{exact:true}).selectOption('3');
await page.getByRole('heading',{name:'Operating Systems',exact:true}).waitFor();
await page.setViewportSize({width:390,height:844});
await page.screenshot({path:'curriculum-cards-mobile.png',fullPage:true});
const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
if(overflow)throw new Error('Mobile curriculum overflows');
await page.reload();
await page.getByRole('heading',{name:'Operating Systems',exact:true}).waitFor();
await page.getByRole('button',{name:'Open Curriculum',exact:true}).first().click();
await page.getByRole('checkbox',{name:'CPU Scheduling',exact:true}).waitFor();
if(!await page.getByRole('checkbox',{name:'CPU Scheduling',exact:true}).isChecked())throw new Error('Progress did not persist');
await page.screenshot({path:'curriculum-subject-mobile.png',fullPage:true});
return {subjectCreated:true,examBeforeUpload:true,reviewRequired:true,editedExtraction:true,topicScopedExamPriority:true,studyTimePersisted:true,topicProgressPersisted:true,multipleSemesters:true,siblingSubjectsPreserved:true,retiredNavigationAbsent:true,mobileNoOverflow:!overflow};
""".replace('TOKEN',json.dumps(token)).replace('BYTES',json.dumps(list(pdf))).replace('EXAM_DATE',json.dumps(str(date.today()+timedelta(days=4))))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','55','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=65)
print(r.stdout);print(r.stderr);assert r.returncode==0
