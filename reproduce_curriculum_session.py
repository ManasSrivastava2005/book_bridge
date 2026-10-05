import json,subprocess,uuid
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 student=User(name='Session isolation fixture',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT);db.add(student);db.commit();token=create_access_token(student.id,'student');staff=db.query(User).filter_by(role=UserRole.LIBRARIAN).first();staff_token=create_access_token(staff.id,'librarian')
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),STUDENT);await page.goto('http://127.0.0.1:5174/curriculum');await page.getByRole('heading',{name:'My Curriculum',exact:true}).waitFor();
await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),STAFF);
const response=page.waitForResponse(r=>r.url().includes('/academic/personal-curriculum'));await page.getByRole('button',{name:'Create or edit personal curriculum',exact:true}).click();const result=await response;if(result.status()!==403)throw new Error('Expected shared token role mismatch');await page.getByText('You do not have permission to perform this action',{exact:true}).waitFor();await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));return {url:page.url(),reproducedStudentScreenUsingStaffToken:true,status:result.status()};
""".replace('STUDENT',json.dumps(token)).replace('STAFF',json.dumps(staff_token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','35','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=45);print(r.stdout);print(r.stderr);assert r.returncode==0
