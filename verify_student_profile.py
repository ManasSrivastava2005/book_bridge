import json,uuid,subprocess
import app.main
from app.database import SessionLocal
from app.models.user import User,UserRole
from app.models.badge import UserBadge
from app.services.auth import create_access_token
with SessionLocal() as db:
 u=User(name='Profile verification',email=uuid.uuid4().hex+'@example.com',hashed_password='unusable',role=UserRole.STUDENT);db.add(u);db.commit();uid=u.id;token=create_access_token(uid,'student')
try:
 program="""await page.goto('http://127.0.0.1:5173/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5173/settings');await page.getByText('No XP earned yet.',{exact:true}).waitFor();await page.getByText('No attempts',{exact:true}).waitFor();const profile=await page.getByRole('heading',{name:'Your learning progress',exact:true}).count();await page.goto('http://127.0.0.1:5173/dashboard');await page.getByText('No attempts',{exact:true}).waitFor();const fake=await page.getByText('6h 20m',{exact:true}).count();await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('token');});await page.goto('http://127.0.0.1:5173/login');return {profileProgress:profile===1,fabricatedReadingTimeAbsent:fake===0};""".replace('TOKEN',json.dumps(token))
 r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','student-final-checks-vm','browser','run','--stdin','--no-snapshot-diff','--timeout','40','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=50);print(r.stdout);print(r.stderr)
finally:
 with SessionLocal() as db:db.query(UserBadge).filter_by(user_id=uid).delete();db.query(User).filter_by(id=uid).delete();db.commit()
