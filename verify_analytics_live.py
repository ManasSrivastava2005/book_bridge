"""Opt-in Phase 5 analytics checks using temporary library/loan fixtures."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import uuid
import httpx
from app.database import SessionLocal
from app.models.library import Library
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.user import User, UserRole
from app.routers.admin import database_now
from app.services.auth import create_access_token

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--browser-session',required=True)
args=parser.parse_args()
marker='Analytics verification '+uuid.uuid4().hex[:8]
library_id=None;book_id=None
program=r'''
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),TOKEN);
await page.goto('http://127.0.0.1:5173/admin/dashboard');
await page.getByRole('heading',{name:'Circulation analytics',exact:true}).waitFor();
const section=page.getByRole('region',{name:'Circulation analytics',exact:true});
await section.getByRole('button',{name:'Export daily CSV',exact:true}).waitFor();
const filtered=page.waitForResponse(r=>r.url().includes('/admin/analytics?') && r.url().includes('library_id='+LIBRARY));
await page.getByRole('combobox',{name:'Analytics library',exact:true}).selectOption(String(LIBRARY));
const result=await filtered;if(result.status()!==200)throw new Error('Library analytics failed');
const data=await result.json();
if(data.totals.checkouts!==1 || data.totals.returns!==1 || data.totals.unique_borrowers!==1)throw new Error('Unexpected totals');
const period=page.waitForResponse(r=>r.url().includes('/admin/analytics?') && r.url().includes('days=7'));
await page.getByRole('combobox',{name:'Analytics period',exact:true}).selectOption('7');
if((await period).status()!==200)throw new Error('Period filter failed');
await section.getByText('Daily activity table',{exact:true}).click();
await section.getByRole('table').waitFor();
if(await section.locator('tbody tr').count()!==7)throw new Error('Wrong daily row count');
const pending=page.waitForEvent('download');
await section.getByRole('button',{name:'Export daily CSV',exact:true}).click();
const download=await pending;
await download.saveAs('analytics-verification.csv');
await page.setViewportSize({width:390,height:844});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');
await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_user');});
await page.goto('http://127.0.0.1:5173/login');
if(errors.length)throw new Error(errors.join(';'));
return {libraryFilter:true,periodFilter:true,exactCounts:true,dailyTable:true,csvDownload:true,mobile:true,pageErrors:errors};
'''
try:
 with SessionLocal() as db:
  staff=db.query(User).filter(User.role.in_([UserRole.LIBRARIAN,UserRole.ADMIN])).first()
  student=db.query(User).filter(User.role==UserRole.STUDENT).first()
  assert staff and student
  token=create_access_token(staff.id,staff.role.value)
  student_token=create_access_token(student.id,student.role.value)
  library=Library(id=1_000_000_000+int(uuid.uuid4().hex[:7],16),name=marker,code='AV'+uuid.uuid4().hex[:12],campus='Verification');db.add(library);db.flush();library_id=library.id
  book=Book(title=marker,author='Verification fixture',library_id=library_id,category='Analytics fixture',total_copies=1,available_copies=0);db.add(book);db.flush();book_id=book.id
  now=database_now(db)-timedelta(seconds=1)
  db.add_all([BorrowRecord(user_id=student.id,book_id=book_id,borrowed_at=now,due_date=now-timedelta(days=1),status='borrowed'),
              BorrowRecord(user_id=student.id,book_id=book_id,borrowed_at=now-timedelta(days=45),due_date=now-timedelta(days=31),returned_at=now,status='returned')]);db.commit()
 with httpx.Client(base_url='http://127.0.0.1:8000') as client:
  assert client.get('/admin/analytics').status_code==401
  assert client.get('/admin/analytics',headers={'Authorization':'Bearer '+student_token}).status_code==403
  response=client.get('/admin/analytics',params={'days':7,'library_id':library_id},headers={'Authorization':'Bearer '+token})
  assert response.status_code==200,response.text
  data=response.json();assert data['totals']=={'checkouts':1,'returns':1,'unique_borrowers':1}
  assert [row['count'] for row in data['overdue']]==[1,0,0]
  assert data['categories']==[{'category':'Analytics fixture','checkouts':1}]
 constants='const TOKEN='+json.dumps(token)+';const LIBRARY='+str(library_id)+';\n'
 result=subprocess.run([str(Path.home()/'AppData/Roaming/npm/webcmd.cmd'),'--profile','bookbridge-notes','--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff'],input=constants+program,text=True,capture_output=True,encoding='utf-8',timeout=65)
 print((result.stdout+result.stderr).replace(token,'[redacted]').replace(student_token,'[redacted]'))
 assert result.returncode==0,'Browser verification failed'
 receipt=json.loads(result.stdout)
 assert receipt['ok']
 artifact=next(a for a in receipt['artifacts'] if a['filename']=='analytics-verification.csv')
 csv=(Path.home()/'.webcmd/cache/browser-run'/artifact['artifactId']/artifact['filename']).read_text(encoding='utf-8-sig')
 rows=csv.splitlines();assert rows[0]=='Date,Checkouts,Returns' and len(rows)==8
 assert sum(int(row.split(',')[1]) for row in rows[1:])==1
 assert sum(int(row.split(',')[2]) for row in rows[1:])==1
 print('PostgreSQL aggregates, authorization and downloaded CSV bytes: passed')
finally:
 with SessionLocal() as db:
  if book_id:
   db.query(BorrowRecord).filter(BorrowRecord.book_id==book_id).delete(synchronize_session=False)
   db.query(Book).filter(Book.id==book_id,Book.title==marker).delete(synchronize_session=False)
  if library_id:db.query(Library).filter(Library.id==library_id,Library.name==marker).delete(synchronize_session=False)
  db.commit()
