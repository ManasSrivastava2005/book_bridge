"""Opt-in staff UI/PostgreSQL checks using only isolated catalog/loan fixtures."""
import argparse
import json
from pathlib import Path
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import httpx
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.library import Library
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.notification import Notification
from app.models.digital_resource import DigitalResource
from app.services.auth import create_access_token

parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--browser-session',required=True);args=parser.parse_args()
with SessionLocal() as db:
 staff=db.query(User).filter(User.role.in_([UserRole.LIBRARIAN,UserRole.ADMIN])).first()
 students=db.query(User).filter(User.role==UserRole.STUDENT).order_by(User.id).limit(2).all()
 assert staff and len(students)==2,'Existing staff and two students are needed; no users will be created.'
 staff_token=create_access_token(staff.id,staff.role.value)
 student_token=create_access_token(students[0].id,'student')
 student_ids=[s.id for s in students]

label='Phase5 verification '+uuid.uuid4().hex[:8]
ids=[]
program=r'''
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),STAFF);
await page.goto('http://127.0.0.1:5173/admin/dashboard');
await page.getByRole('heading',{name:'Librarian Management Hub',exact:true}).waitFor();
await page.getByRole('heading',{name:'Inventory pressure',exact:true}).waitFor();
if(await page.getByText('Confidence: 89.4%',{exact:false}).count())throw new Error('Fake ML confidence visible');
await page.getByRole('link',{name:'Manage circulation',exact:true}).click();
await page.getByRole('heading',{name:'Circulation',exact:true}).waitFor();
await page.getByRole('combobox',{name:'Student',exact:true}).selectOption(String(STUDENTS[0]));
await page.getByRole('combobox',{name:'Book',exact:true}).selectOption(String(BOOKS[0]));
const issue=page.waitForResponse(r=>r.url().endsWith('/admin/loans') && r.request().method()==='POST');
await page.getByRole('button',{name:'Issue book',exact:true}).click();
if((await issue).status()!==201)throw new Error('Checkout failed');
await page.getByRole('status').filter({hasText:'Book issued'}).waitFor();
await page.getByRole('textbox',{name:'Search circulation',exact:true}).fill(LABEL+' issue');
const issued=page.getByRole('article').filter({hasText:LABEL+' issue'});
await issued.getByRole('button',{name:'Record return',exact:true}).click();
await page.getByRole('button',{name:'Confirm return',exact:true}).click();
await page.getByRole('status').filter({hasText:'Return recorded'}).waitFor();
await page.getByRole('button',{name:'Returned',exact:true}).click();
await page.getByRole('article').filter({hasText:LABEL+' issue'}).waitFor();
await page.getByRole('button',{name:'Overdue',exact:true}).click();
await page.getByRole('textbox',{name:'Search circulation',exact:true}).fill(LABEL+' overdue');
await page.getByRole('article').filter({hasText:LABEL+' overdue'}).waitFor();
await page.getByRole('button',{name:'Reservations',exact:true}).click();
await page.getByRole('textbox',{name:'Search circulation',exact:true}).fill(LABEL+' hold');
await page.getByRole('button',{name:'Release held copy',exact:true}).click();
await page.getByRole('button',{name:'Confirm release',exact:true}).click();
await page.getByRole('status').filter({hasText:'Held copy released'}).waitFor();
await page.getByRole('button',{name:'Release held copy',exact:true}).click();
await page.getByRole('button',{name:'Confirm release',exact:true}).click();
await page.getByRole('status').filter({hasText:'Held copy released'}).waitFor();
await page.getByRole('textbox',{name:'Search circulation',exact:true}).fill(LABEL+' wait');
await page.getByRole('button',{name:'Cancel reservation',exact:true}).click();
await page.getByRole('button',{name:'Confirm cancellation',exact:true}).click();
await page.getByRole('status').filter({hasText:'Reservation cancelled'}).waitFor();
await page.setViewportSize({width:390,height:844});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Circulation mobile overflow');
await page.goto('http://127.0.0.1:5173/admin/resources');
await page.getByRole('heading',{name:'Manage digital resources',exact:true}).waitFor();
await page.getByRole('textbox',{name:'Title',exact:true}).fill(LABEL+' resource');
await page.getByRole('textbox',{name:'Author',exact:true}).fill('Verification fixture');
await page.getByRole('textbox',{name:'Existing PDF / file URL',exact:true}).fill('/uploads/ebooks/verification.pdf');
await page.getByRole('button',{name:'Save resource',exact:true}).click();
await page.getByRole('status').filter({hasText:'Digital resource saved.'}).waitFor();
await page.getByRole('textbox',{name:'Search digital resources',exact:true}).fill(LABEL+' resource');
let article=page.getByRole('article').filter({hasText:LABEL+' resource'});
await article.getByText('Draft',{exact:true}).waitFor();
await article.getByRole('button',{name:'Publish',exact:true}).click();
await article.getByText('Published',{exact:true}).waitFor();
await article.getByRole('button',{name:'Edit metadata',exact:true}).click();
await page.getByRole('textbox',{name:'Description',exact:true}).fill('Verified metadata edit');
await page.getByRole('button',{name:'Save resource',exact:true}).click();
await page.getByRole('status').filter({hasText:'Digital resource saved.'}).waitFor();
await article.getByRole('button',{name:'Move to drafts',exact:true}).click();
await article.getByText('Draft',{exact:true}).waitFor();
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Resource mobile overflow');
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),STUDENT);
await page.goto('http://127.0.0.1:5173/admin/circulation');
await page.waitForURL('**/dashboard');
if(await page.getByRole('heading',{name:'Circulation',exact:true}).count())throw new Error('Student entered staff page');
await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_user');});
await page.goto('http://127.0.0.1:5173/login');
if(errors.length)throw new Error(errors.join('; '));
return {dashboardRealMetrics:true,staffCheckoutReturn:true,overdue:true,heldCopyRelease:true,reservationCancellation:true,digitalDraftPublishEdit:true,mobile:true,studentRouteDenied:true,pageErrors:errors};
'''
try:
 with SessionLocal() as db:
  for suffix,available,total in [('issue',1,1),('hold',0,1),('overdue',0,1),('wait',0,0),('race',1,1)]:
   b=Book(title=label+' '+suffix,author='Verification fixture',available_copies=available,total_copies=total)
   db.add(b);db.flush();ids.append(b.id)
  db.add(BorrowRecord(user_id=student_ids[0],book_id=ids[2],status='borrowed',due_date=datetime.now()-timedelta(days=2)))
  db.add(Reservation(user_id=student_ids[0],book_id=ids[1],status='fulfilled'))
  db.add(Reservation(user_id=student_ids[1],book_id=ids[1],status='pending'))
  db.add(Reservation(user_id=student_ids[0],book_id=ids[3],status='pending'))
  db.commit()
 with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+staff_token}) as client:
  dashboard=client.get('/admin/dashboard');assert dashboard.status_code==200,dashboard.text[:100]
  assert client.get('/admin/overdue-books').status_code==200
 constants='\n'.join(f'const {k}={json.dumps(v)};' for k,v in {'STAFF':staff_token,'STUDENT':student_token,'STUDENTS':student_ids,'BOOKS':ids,'LABEL':label}.items())+'\n'
 command=[str(Path.home()/'AppData/Roaming/npm/webcmd.cmd'),'--profile','bookbridge-notes','--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff']
 result=subprocess.run(command,input=constants+program,text=True,capture_output=True,encoding='utf-8',timeout=65)
 print((result.stdout+result.stderr).replace(staff_token,'[redacted]').replace(student_token,'[redacted]')[:6500])
 assert result.returncode==0,'Staff browser checks failed'
 def checkout(student):
  with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+staff_token}) as client:
   return client.post('/admin/loans',json={'student_id':student,'book_id':ids[4]})
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(checkout,student_ids))
 assert sorted(r.status_code for r in responses)==[201,400]
 loan=next(r.json()['id'] for r in responses if r.status_code==201)
 def return_loan(_):
  with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+staff_token}) as client:
   return client.post(f'/borrows/{loan}/return').status_code
 with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(return_loan,range(2)))
 assert sorted(statuses)==[200,400]
 with SessionLocal() as db:
  assert db.get(Book,ids[0]).available_copies==1
  assert db.get(Book,ids[1]).available_copies==1
  assert db.get(Book,ids[4]).available_copies==1
  resource=db.query(DigitalResource).filter(DigitalResource.title==label+' resource').one()
  assert resource.description=='Verified metadata edit' and not resource.is_published
 print('PostgreSQL verification passed: inventory counts, publication state, one-copy concurrent checkout and repeated return protection.')
finally:
 with SessionLocal() as db:
  if ids:
   db.query(Reservation).filter(Reservation.book_id.in_(ids)).delete(synchronize_session=False)
   db.query(BorrowRecord).filter(BorrowRecord.book_id.in_(ids)).delete(synchronize_session=False)
   db.query(Book).filter(Book.id.in_(ids),Book.author=='Verification fixture').delete(synchronize_session=False)
  db.query(Notification).filter(Notification.message.contains(label)).delete(synchronize_session=False)
  db.query(DigitalResource).filter(DigitalResource.title==label+' resource',DigitalResource.author=='Verification fixture').delete(synchronize_session=False)
  db.commit()
