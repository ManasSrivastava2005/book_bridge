import uuid,json,subprocess
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User,UserRole
from app.models.curriculum import Curriculum
from app.models.academic_profile import AcademicProfile
from app.models.student_exam import StudentExam
from app.services.auth import create_access_token
uid=None
try:
 with SessionLocal() as db:
  u=User(name='Exam verification',email=uuid.uuid4().hex+'@example.com',hashed_password='unusable',role=UserRole.STUDENT);db.add(u);db.flush();uid=u.id
  db.add(AcademicProfile(user_id=uid,subject_ids=[],custom_subjects=['Robotics']));db.commit();token=create_access_token(uid,'student')
 program="""await page.goto('http://127.0.0.1:5173/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5173/settings');await page.getByLabel('Exam subject').selectOption('custom:Robotics');await page.getByLabel('Exam name',{exact:true}).fill('Verification midterm');await page.getByLabel('Date',{exact:true}).fill('2026-12-01');await page.getByRole('button',{name:'Add exam',exact:true}).click();await page.getByText('Exam saved.',{exact:true}).waitFor();const saved=await page.getByText('Robotics · Verification midterm',{exact:true}).innerText();await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));await page.goto('http://127.0.0.1:5173/login');return {saved};""".replace('TOKEN',json.dumps(token))
 r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','student-reading-check-6p','browser','run','--stdin','--no-snapshot-diff','--timeout','30','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=40);print(r.stdout);print(r.stderr)
finally:
 if uid:
  with SessionLocal() as db:
   db.query(StudentExam).filter_by(user_id=uid).delete();db.query(AcademicProfile).filter_by(user_id=uid).delete();db.query(User).filter_by(id=uid).delete();db.commit()
