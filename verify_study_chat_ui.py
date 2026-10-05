import json,subprocess,uuid
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.study import StudyRoom,StudyMessage,StudyMember
from app.services.auth import create_access_token
with fixture.database.SessionLocal() as db:
 users=[User(name='Chat owner',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT),User(name='Chat member',email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)]
 db.add_all(users);db.commit();owner,other=[u.id for u in users];token=create_access_token(owner,'student');second=create_access_token(other,'student')
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5174/study-together');
await page.getByText('Create a study room',{exact:true}).click();await page.getByLabel('Room title',{exact:true}).fill('Chat upgrade acceptance');await page.getByRole('button',{name:'Create room',exact:true}).click();await page.getByRole('heading',{name:'Chat upgrade acceptance',exact:true}).waitFor();
const roomId=page.url().split('/').pop();await page.getByLabel('Your message',{exact:true}).fill('What is deadlock?');await page.getByRole('button',{name:'Post message',exact:true}).click();await page.getByText('What is deadlock?',{exact:true}).waitFor();
await page.getByRole('button',{name:'Edit message',exact:true}).click();await page.getByLabel('Edit your message',{exact:true}).fill('Explain deadlock conditions.');await page.getByRole('button',{name:'Save message',exact:true}).click();await page.getByText('Explain deadlock conditions.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Edit room details',exact:true}).click();await page.getByLabel('Room description',{exact:true}).fill('Discuss operating systems together.');await page.getByRole('button',{name:'Save room details',exact:true}).click();await page.getByText('Room details updated.',{exact:true}).waitFor();
await page.evaluate(async args=>{const r=await fetch('http://127.0.0.1:8001/study/rooms/'+args.id+'/join',{method:'POST',headers:{Authorization:'Bearer '+args.token}});if(!r.ok)throw new Error('Join failed');},{id:roomId,token:SECOND});
await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),SECOND);await page.reload();await page.getByRole('heading',{name:'Participants (2)',exact:true}).waitFor();
await page.getByRole('button',{name:'Reply',exact:true}).click();await page.getByLabel('Your message',{exact:true}).fill('Mutual exclusion is one condition.');await page.getByRole('button',{name:'Post message',exact:true}).click();await page.getByText('Mutual exclusion is one condition.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Leave room',exact:true}).click();await page.getByRole('button',{name:'Confirm',exact:true}).click();await page.getByRole('button',{name:'Join room',exact:true}).click();await page.getByRole('heading',{name:'Participants (2)',exact:true}).waitFor();
await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.reload();
const question=page.locator('article').filter({hasText:'Explain deadlock conditions.'}).first();await question.getByRole('button',{name:'Remove message',exact:true}).click();await page.getByRole('button',{name:'Confirm',exact:true}).click();await page.getByText('This message was deleted',{exact:true}).waitFor();
await page.reload();await page.getByText('This message was deleted',{exact:true}).waitFor();
const poll=page.waitForResponse(r=>r.url().includes('/messages')&&r.request().method()==='GET');await poll;
await page.goto('http://127.0.0.1:5174/dashboard');await page.getByRole('heading',{name:'Your study rooms',exact:true}).waitFor();await page.getByRole('link',{name:/Chat upgrade acceptance/}).waitFor();await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));return {url:page.url(),roomId,create:true,reply:true,edit:true,tombstone:true,rejoin:true,polling:true,dashboard:true};
""".replace('SECOND',json.dumps(second)).replace('TOKEN',json.dumps(token))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','50','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=60);print(r.stdout);print(r.stderr);assert r.returncode==0
with fixture.database.SessionLocal() as db:
 room=db.query(StudyRoom).filter_by(owner_id=owner).one();rows=db.query(StudyMessage).filter_by(room_id=room.id).order_by(StudyMessage.id).all();assert len(rows)==2 and rows[0].deleted_at and rows[0].edited_at and rows[1].reply_to_id==rows[0].id;assert db.get(StudyMember,(room.id,other)).left_at is None
print('Retained message IDs, reply reference, edit/delete timestamps and rejoined membership verified.')
