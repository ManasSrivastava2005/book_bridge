import json,subprocess
import app.main
from app.database import SessionLocal
from app.models.user import User,UserRole
from app.services.auth import create_access_token
with SessionLocal() as db:
 u=db.query(User).filter(User.role.in_([UserRole.LIBRARIAN,UserRole.ADMIN])).first();token=create_access_token(u.id,u.role.value)
program="""await page.goto('http://127.0.0.1:5173/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);const results=[];for(const route of ['dashboard','books','circulation','resources','contributions','curricula','quizzes','announcements','analytics','qr','users','study-moderation']){await page.goto('http://127.0.0.1:5173/admin/'+route);await page.waitForLoadState('networkidle');results.push({route,headings:await page.locator('h1').allTextContents(),alerts:await page.getByRole('alert').allTextContents()});}await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));await page.goto('http://127.0.0.1:5173/login');return results;""".replace('TOKEN',json.dumps(token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','student-final-checks-vm','browser','run','--stdin','--no-snapshot-diff','--timeout','50','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=60);print(r.stdout);print(r.stderr)
