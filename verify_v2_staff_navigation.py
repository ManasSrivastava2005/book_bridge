"""Read-only staff navigation and role-boundary browser acceptance."""
import json,subprocess
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 staff=db.query(User).filter_by(role=UserRole.LIBRARIAN).first()
 student=db.query(User).filter_by(role=UserRole.STUDENT).first()
 staff_token=create_access_token(staff.id,'librarian');student_token=create_access_token(student.id,'student')
program="""
await page.goto('http://127.0.0.1:5174/librarian/login');
await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),STAFF_TOKEN);
await page.goto('http://127.0.0.1:5174/admin/dashboard');
await page.getByRole('heading',{name:'Librarian Management Hub',exact:true}).waitFor();
const links=await page.getByRole('navigation',{name:'Staff navigation',exact:true}).getByRole('link').evaluateAll(items=>items.map(a=>({name:a.textContent.trim(),path:a.getAttribute('href')})));
if(links.some(x=>['Users','Curriculum','Notes Library','My Contributions'].includes(x.name)))throw new Error('Redundant navigation remains');
const checked=[];
for(const link of links){await page.goto('http://127.0.0.1:5174'+link.path);await page.locator('main h1').first().waitFor();if(!page.url().endsWith(link.path))throw new Error('Unexpected redirect: '+link.path);checked.push({path:link.path,heading:await page.locator('main h1').first().innerText()});}
await page.setViewportSize({width:390,height:844});
await page.getByRole('button',{name:'Open navigation',exact:true}).click();
await page.getByRole('navigation',{name:'Staff navigation',exact:true}).getByRole('link',{name:'Student Data',exact:true}).click();
await page.getByRole('heading',{name:'Student Data',exact:true}).waitFor();
await page.setViewportSize({width:1280,height:900});
await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),STUDENT_TOKEN);
await page.goto('http://127.0.0.1:5174/admin/student-data');
await page.waitForURL('**/dashboard');
const denied=await page.evaluate(async token=>{const paths=['/admin/student-data','/admin/profile','/admin/reservations','/admin/digital-resources'];const results=[];for(const path of paths){const r=await fetch('http://127.0.0.1:8001'+path,{headers:{Authorization:'Bearer '+token}});results.push(r.status);}return results;},STUDENT_TOKEN);
if(denied.some(status=>status!==403))throw new Error('Staff API role boundary failed');
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));
await page.goto('http://127.0.0.1:5174/librarian/login');
return {links:checked,mobileNavigation:true,studentStaffApiStatuses:denied,studentStaffRouteDenied:true};
""".replace('STAFF_TOKEN',json.dumps(staff_token)).replace('STUDENT_TOKEN',json.dumps(student_token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','55','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=65)
print(r.stdout);print(r.stderr);assert r.returncode==0
