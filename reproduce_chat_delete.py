import json,subprocess,uuid
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.study import StudyRoom,StudyMember,StudyMessage
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 user=User(name='Delete acceptance',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 db.add(user);db.flush()
 room=StudyRoom(owner_id=user.id,title='Delete visibility check',subject='CS',description='Isolated fixture',is_private=False)
 db.add(room);db.flush();db.add(StudyMember(room_id=room.id,user_id=user.id,role='OWNER'))
 for i in range(25):db.add(StudyMessage(room_id=room.id,user_id=user.id,body=f'Fixture message {i}',client_id=str(uuid.uuid4())))
 db.commit();rid=room.id;token=create_access_token(user.id,'student')
program=r"""
await page.setViewportSize({width:1200,height:800});
await page.goto('http://127.0.0.1:5174/login');
await page.evaluate(t=>{localStorage.removeItem('bookbridge_token');sessionStorage.setItem('bookbridge_token',t);},TOKEN);
await page.goto('http://127.0.0.1:5174/study-together/ROOM');
await page.getByText('Fixture message 24',{exact:true}).waitFor();
await page.locator('article').filter({hasText:'Fixture message 24'}).getByRole('button',{name:'Remove message',exact:true}).click();
const visible=await page.getByRole('button',{name:'Confirm',exact:true}).evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=window.innerHeight;});
return {confirmationInViewport:visible,problemReproduced:!visible};
""".replace('TOKEN',json.dumps(token)).replace('ROOM',str(rid))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=45)
print(r.stdout);print(r.stderr);assert r.returncode==0
