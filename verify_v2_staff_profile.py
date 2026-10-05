import subprocess,json
from app.database import SessionLocal
from app.models.user import User,UserRole
from app.models.library import Library
from app.services.auth import create_access_token
with SessionLocal() as db:
 u=db.query(User).filter_by(role=UserRole.LIBRARIAN).first();token=create_access_token(u.id,'librarian')
program="""await page.goto('http://127.0.0.1:5173/login');await page.getByRole('link',{name:'Librarian / Admin sign in',exact:true}).waitFor();await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5173/admin/profile');await page.getByRole('heading',{name:'Staff profile',exact:true}).waitFor();await page.getByText('Work email',{exact:true}).waitFor();const academicAbsent=await page.getByText('XP history',{exact:true}).count()===0;await page.goto('http://127.0.0.1:5173/academic-plan');await page.getByRole('heading',{name:'Librarian Management Hub',exact:true}).waitFor();const redirect=page.url().endsWith('/admin/dashboard');await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('heading',{name:'Staff sign in',exact:true}).waitFor();await page.goto('http://127.0.0.1:5173/admin/profile');await page.getByRole('heading',{name:'Staff sign in',exact:true}).waitFor();return {staffProfile:true,academicAbsent,staffRedirect:redirect,logoutAndProtectedReload:true};""".replace('TOKEN',json.dumps(token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','40','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=50);print(r.stdout);print(r.stderr)
