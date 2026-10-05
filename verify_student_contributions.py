import uuid,json,subprocess
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User,UserRole
from app.models.contribution import Contribution
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.services import contributions as storage
from app.services.auth import create_access_token
uid=None
try:
 with SessionLocal() as db:
  u=User(name='Upload verification',email=uuid.uuid4().hex+'@example.com',hashed_password='unusable',role=UserRole.STUDENT);db.add(u);db.commit();uid=u.id;token=create_access_token(uid,'student')
 program="""await page.goto('http://127.0.0.1:5173/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5173/contributions');await page.getByLabel('Title',{exact:true}).fill('Verification study notes');await page.getByLabel('Subject',{exact:true}).fill('Operating Systems');await page.locator('input[type=file]').setInputFiles({name:'verification.txt',mimeType:'text/plain',buffer:new TextEncoder().encode('Temporary academic upload fixture.')});await page.getByRole('button',{name:'Submit for review',exact:true}).click();await page.getByText('Operating Systems · PENDING',{exact:true}).waitFor();const status=await page.getByText('Operating Systems · PENDING',{exact:true}).innerText();await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));await page.goto('http://127.0.0.1:5173/login');return {status};""".replace('TOKEN',json.dumps(token))
 r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','student-plan-verification-vt','browser','run','--stdin','--no-snapshot-diff','--timeout','30','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=40);print(r.stdout);print(r.stderr)
finally:
 if uid:
  with SessionLocal() as db:
   for row in db.query(Contribution).filter_by(user_id=uid).all():storage.private_path(row.storage_name).unlink(missing_ok=True);db.delete(row)
   db.flush();db.query(User).filter_by(id=uid).delete();db.commit()
