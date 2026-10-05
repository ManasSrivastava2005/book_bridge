"""Opt-in Study Together verification. Removes only this run's room and posts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import uuid
import httpx
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User, UserRole
from app.models.study import StudyRoom, StudyMember, StudyMessage
from app.services.auth import create_access_token

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--browser-session',required=True)
args=parser.parse_args()
marker='Study verification '+uuid.uuid4().hex[:10]
with SessionLocal() as db:
 users=db.query(User).filter(User.role==UserRole.STUDENT).order_by(User.id).limit(2).all()
 assert len(users)==2
 tokens=[create_access_token(user.id,user.role.value) for user in users]
 ids=[user.id for user in users]
program=r'''
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),OWNER);
await page.goto('http://127.0.0.1:5173/study-together');
await page.getByRole('heading',{name:'Study Together',exact:true}).waitFor();
await page.getByText('Create a study room',{exact:true}).click();
await page.getByLabel('Room title',{exact:true}).fill(MARKER);
await page.getByLabel('Subject',{exact:true}).fill('Operating Systems');
await page.getByLabel('Study goal',{exact:true}).fill('Temporary collaboration verification');
const created=page.waitForResponse(r=>r.url().endsWith('/study/rooms') && r.request().method()==='POST');
await page.getByRole('button',{name:'Create room',exact:true}).click();
const response=await created;if(response.status()!==201)throw new Error('Create failed');
const room=await response.json();
await page.getByRole('heading',{name:MARKER,exact:true}).waitFor();
await page.getByLabel('Your message',{exact:true}).fill('Owner question: how does scheduling work?');
await page.getByRole('button',{name:'Post message',exact:true}).click();
await page.getByText('Owner question: how does scheduling work?',{exact:true}).waitFor();
await page.reload();
await page.getByText('Owner question: how does scheduling work?',{exact:true}).waitFor();
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),MEMBER);
await page.goto('http://127.0.0.1:5173/study-together/'+room.id);
await page.getByRole('button',{name:'Join room',exact:true}).waitFor();
if(await page.getByText('Owner question: how does scheduling work?',{exact:true}).count())throw new Error('Nonmember saw discussion');
await page.getByRole('button',{name:'Join room',exact:true}).click();
await page.getByText('Owner question: how does scheduling work?',{exact:true}).waitFor();
await page.getByLabel('Your message',{exact:true}).fill('Member answer: the scheduler selects a ready process.');
await page.getByRole('button',{name:'Post message',exact:true}).click();
await page.getByText('Member answer: the scheduler selects a ready process.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Leave room',exact:true}).click();
await page.getByRole('button',{name:'Confirm',exact:true}).click();
await page.getByRole('button',{name:'Join room',exact:true}).waitFor();
await page.getByRole('button',{name:'Join room',exact:true}).click();
await page.getByText('Member answer: the scheduler selects a ready process.',{exact:true}).waitFor();
await page.setViewportSize({width:390,height:844});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),OWNER);
await page.goto('http://127.0.0.1:5173/study-together/'+room.id);
const reply=page.getByRole('article').filter({hasText:'Member answer: the scheduler selects a ready process.'});
await reply.getByRole('button',{name:'Remove message',exact:true}).click();
await page.getByRole('button',{name:'Confirm',exact:true}).click();
await page.getByRole('status').filter({hasText:'Message removed.'}).waitFor();
await page.getByRole('button',{name:'Archive room',exact:true}).click();
await page.getByRole('button',{name:'Confirm',exact:true}).click();
await page.getByText('Archived — discussion is read-only.',{exact:true}).waitFor();
if(await page.getByLabel('Your message',{exact:true}).count())throw new Error('Archived composer visible');
await page.getByRole('button',{name:'Reopen room',exact:true}).click();
await page.getByRole('button',{name:'Confirm',exact:true}).click();
await page.getByLabel('Your message',{exact:true}).waitFor();
await page.getByRole('link',{name:'← All study rooms',exact:true}).click();
await page.getByRole('button',{name:'My rooms',exact:true}).click();
await page.getByRole('heading',{name:MARKER,exact:true}).waitFor();
await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_user');});
await page.goto('http://127.0.0.1:5173/login');
if(errors.length)throw new Error(errors.join(';'));
return {create:true,persistence:true,nonmemberIsolation:true,joinLeave:true,twoUserDiscussion:true,ownerModeration:true,archiveReopen:true,myRooms:true,mobile:true,pageErrors:errors};
'''
try:
 constants='const OWNER='+json.dumps(tokens[0])+';const MEMBER='+json.dumps(tokens[1])+';const MARKER='+json.dumps(marker)+';\n'
 command=[str(Path.home()/'AppData/Roaming/npm/webcmd.cmd'),'--profile','bookbridge-notes','--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff']
 result=subprocess.run(command,input=constants+program,text=True,capture_output=True,encoding='utf-8',timeout=65)
 output=result.stdout+result.stderr
 for token in tokens:output=output.replace(token,'[redacted]')
 print(output)
 assert result.returncode==0 and json.loads(result.stdout)['ok'],'Browser verification failed'
 with SessionLocal() as db:
  room=db.query(StudyRoom).filter(StudyRoom.title==marker).one();rid=room.id
  assert room.owner_id==ids[0] and not room.archived
  assert db.query(StudyMember).filter(StudyMember.room_id==rid).count()==2
  assert db.query(StudyMessage).filter(StudyMessage.room_id==rid).count()==1
 key=str(uuid.uuid4())
 def post(_):
  with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+tokens[1]}) as client:
   return client.post(f'/study/rooms/{rid}/messages',json={'body':'Concurrent retry fixture','client_id':key})
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(post,range(2)))
 assert all(response.status_code==201 for response in responses)
 assert responses[0].json()==responses[1].json()
 with SessionLocal() as db:
  assert db.query(StudyMessage).filter(StudyMessage.room_id==rid,StudyMessage.client_id==key).count()==1
 print('PostgreSQL persistence and concurrent duplicate-post prevention: passed')
finally:
 with SessionLocal() as db:
  rooms=db.query(StudyRoom).filter(StudyRoom.title==marker,StudyRoom.owner_id==ids[0]).all()
  for room in rooms:
   db.query(StudyMessage).filter(StudyMessage.room_id==room.id).delete(synchronize_session=False)
   db.query(StudyMember).filter(StudyMember.room_id==room.id).delete(synchronize_session=False)
   db.delete(room)
  db.commit()
