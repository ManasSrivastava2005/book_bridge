import uuid,json,subprocess
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User,UserRole
from app.models.curriculum import Curriculum,CurriculumNode,SubjectEnrollment
from app.models.academic_profile import AcademicProfile
from app.models.topic_progress import TopicProgress
from app.models.badge import UserBadge
from app.services.auth import create_access_token
uid=cid=None
try:
 with SessionLocal() as db:
  u=User(name='Curriculum verification',email=uuid.uuid4().hex+'@example.com',hashed_password='unusable',role=UserRole.STUDENT);db.add(u);db.flush();uid=u.id
  c=Curriculum(family=str(uuid.uuid4()),title='Verification curriculum',college='Test',program='CS',branch='CS',semester=1);db.add(c);db.flush();cid=c.id
  s=CurriculumNode(curriculum_id=cid,kind='subject',title='OS fixture');db.add(s);db.flush()
  unit=CurriculumNode(curriculum_id=cid,parent_id=s.id,kind='unit',title='Memory');db.add(unit);db.flush()
  t=CurriculumNode(curriculum_id=cid,parent_id=unit.id,kind='topic',title='Paging fixture');db.add(t);db.flush()
  db.add(AcademicProfile(user_id=uid,curriculum_id=cid,subject_ids=[s.id],custom_subjects=[]));db.commit();token=create_access_token(uid,'student')
 program="""await page.goto('http://127.0.0.1:5173/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5173/curriculum');await page.getByRole('checkbox',{name:'Paging fixture'}).click();await page.getByRole('heading',{name:'OS fixture · 100%',exact:true}).waitFor();const title=await page.getByRole('heading',{name:'OS fixture · 100%',exact:true}).innerText();await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));await page.goto('http://127.0.0.1:5173/login');return {progress:title};""".replace('TOKEN',json.dumps(token))
 r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','student-reading-check-6p','browser','run','--stdin','--no-snapshot-diff','--timeout','30','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=40);print(r.stdout);print(r.stderr)
finally:
 with SessionLocal() as db:
  if uid:
   for model in (UserBadge,TopicProgress,SubjectEnrollment,AcademicProfile):db.query(model).filter_by(user_id=uid).delete()
  if cid:
   for kind in ('topic','unit','subject'):db.query(CurriculumNode).filter_by(curriculum_id=cid,kind=kind).delete()
   db.query(Curriculum).filter_by(id=cid).delete()
  if uid:db.query(User).filter_by(id=uid).delete()
  db.commit()
