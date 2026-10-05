"""Run only against the isolated acceptance database/server, never working data."""
import json
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
import httpx
import verification_v2_server as fixture
from app.models.user import User, UserRole
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.services.auth import create_access_token

assert fixture.database.engine.url.database.startswith('bookbridge_v2_restore_')
name='V2 circulation '+uuid.uuid4().hex[:8]
with fixture.database.SessionLocal() as db:
 staff=db.query(User).filter_by(role=UserRole.LIBRARIAN).first()
 students=[User(name=name+str(i),email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT) for i in range(2)]
 book=Book(title=name,author='Fixture',total_copies=1,available_copies=1)
 db.add_all([*students,book]);db.commit()
 ids=[u.id for u in students];bid=book.id;token=create_access_token(staff.id,'librarian')
headers={'Authorization':'Bearer '+token}
def issue(uid):
 return httpx.post('http://127.0.0.1:8001/admin/loans',headers=headers,json={'student_id':uid,'book_id':bid,'request_id':str(uuid.uuid4())},timeout=20)
with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(issue,ids))
assert sorted(r.status_code for r in responses)==[201,409], [r.status_code for r in responses]
loan=next(r.json() for r in responses if r.status_code==201)
def returned(_):return httpx.post(f"http://127.0.0.1:8001/borrows/{loan['id']}/return",headers=headers,timeout=20)
with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(returned,range(2)))
assert all(r.status_code==200 for r in responses)
with fixture.database.SessionLocal() as db:
 assert db.get(Book,bid).available_copies==1
 assert db.query(BorrowRecord).filter_by(book_id=bid).count()==1
 db.add(Reservation(user_id=ids[0],book_id=bid,status='pending'));db.commit()
print('PostgreSQL concurrent checkouts and repeated returns preserve single-copy inventory.')
program="""
await page.goto('http://127.0.0.1:5174/librarian/login');
await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/admin/circulation?view=reservations');
await page.getByLabel('Search circulation',{exact:true}).fill(TITLE);
let card=page.locator('article').filter({hasText:TITLE});
await card.getByRole('button',{name:'Mark ready for pickup',exact:true}).click();
await page.getByRole('button',{name:'Confirm ready for pickup',exact:true}).click();
await page.getByText('Copy marked ready for pickup. Student notified.',{exact:true}).waitFor();
await card.getByRole('button',{name:'Prepare checkout',exact:true}).click();
await page.getByLabel('Find student',{exact:true}).fill(TITLE);
await page.getByLabel('Find book',{exact:true}).fill(TITLE);
await page.getByRole('button',{name:'Review checkout',exact:true}).click();
await page.getByRole('button',{name:'Confirm issue',exact:true}).click();
await page.getByText('Book issued. Loan and reservation history updated.',{exact:true}).waitFor();
await page.getByLabel('Reservation status',{exact:true}).selectOption('fulfilled');
await card.getByText('Fulfilled — issued to student',{exact:true}).waitFor();
await page.reload();
await page.getByLabel('Search circulation',{exact:true}).fill(TITLE);
await page.getByLabel('Reservation status',{exact:true}).selectOption('fulfilled');
await page.locator('article').filter({hasText:TITLE}).getByText('Fulfilled — issued to student',{exact:true}).waitFor();
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));
return {url:page.url(),readyAndIssue:true,historyAfterReload:true};
""".replace('TOKEN',json.dumps(token)).replace('TITLE',json.dumps(name))
result=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55)
print(result.stdout);print(result.stderr)
if result.returncode:raise RuntimeError('Circulation browser verification failed')
with fixture.database.SessionLocal() as db:
 row=db.query(Reservation).filter_by(book_id=bid).one()
 assert row.status=='fulfilled' and row.loan_id
 assert db.get(Book,bid).available_copies==0
 assert db.query(BorrowRecord).filter_by(book_id=bid,status='borrowed').count()==1
print('Isolated database confirms linked fulfillment and inventory after UI checkout.')
