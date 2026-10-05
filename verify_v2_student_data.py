"""Student Data UI acceptance in the isolated restored database."""
import json,subprocess,uuid
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.library import Library
from app.models.academic_profile import AcademicProfile
from app.services.auth import create_access_token
name='V2 Student Data '+uuid.uuid4().hex[:8]
with fixture.database.SessionLocal() as db:
 staff=db.query(User).filter_by(role=UserRole.LIBRARIAN).first();token=create_access_token(staff.id,'librarian')
 library=db.query(Library).filter_by(is_active=True).first();lid=library.id
 student=User(name=name,email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT,student_id=uuid.uuid4().hex[:10],branch='CS',semester=3)
 db.add(student);db.flush();sid=student.id
 db.add(AcademicProfile(user_id=sid,college='Acceptance College',program='BTech',custom_subjects=['Acceptance Operating Systems']));db.commit()
program="""
await page.goto('http://127.0.0.1:5174/librarian/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/admin/users');
await page.getByRole('heading',{name:'Student Data',exact:true}).waitFor();
await page.getByLabel('Search students',{exact:true}).fill(NAME);
await page.getByLabel('Branch',{exact:true}).selectOption('CS');
await page.getByLabel('Semester',{exact:true}).selectOption('3');
await page.getByLabel('Membership filter',{exact:true}).selectOption('0');
await page.locator('article').filter({hasText:NAME}).getByRole('button',{name:'View student',exact:true}).click();
await page.getByText('Acceptance Operating Systems',{exact:true}).waitFor();
await page.getByLabel('Library membership',{exact:true}).selectOption(LIBRARY);
await page.getByRole('button',{name:'Save membership',exact:true}).click();
await page.getByText('Library membership updated.',{exact:true}).waitFor();
await page.getByRole('link',{name:'Issue book to student',exact:true}).click();
await page.getByLabel('Student',{exact:true}).locator('option').filter({hasText:NAME}).waitFor({state:'attached'});
const selected=await page.getByLabel('Student',{exact:true}).inputValue();
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));
return {url:page.url(),directoryFilters:true,academicDetails:true,membershipSaved:true,selectedStudent:selected};
""".replace('TOKEN',json.dumps(token)).replace('NAME',json.dumps(name)).replace('LIBRARY',json.dumps(str(lid)))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55)
print(r.stdout);print(r.stderr)
assert r.returncode==0
result=json.loads(r.stdout);assert result['result']['selectedStudent']==str(sid)
with fixture.database.SessionLocal() as db:assert db.get(User,sid).library_id==lid
print('Membership persisted and circulation handoff selected the correct student.')
