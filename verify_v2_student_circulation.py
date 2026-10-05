import json,subprocess,uuid,httpx
import verification_v2_server as fixture
from app.models.user import User,UserRole
from app.models.book import Book
from app.services.auth import create_access_token
name='V2 student circulation '+uuid.uuid4().hex[:8]
with fixture.database.SessionLocal() as db:
 staff=db.query(User).filter_by(role=UserRole.LIBRARIAN).first();staff_token=create_access_token(staff.id,'librarian')
 student=User(name=name,email=uuid.uuid4().hex+'@example.com',hashed_password='disabled',role=UserRole.STUDENT)
 book=Book(title=name,author='Fixture',total_copies=1,available_copies=1)
 db.add_all([student,book]);db.commit();sid=student.id;bid=book.id;token=create_access_token(sid,'student')
staff_headers={'Authorization':'Bearer '+staff_token}
r=httpx.post('http://127.0.0.1:8001/admin/loans',headers=staff_headers,json={'student_id':sid,'book_id':bid,'request_id':str(uuid.uuid4())});r.raise_for_status();loan_id=r.json()['id']
program="""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/my-books');
await page.getByRole('heading',{name:'My Library',exact:true}).waitFor();
await page.getByRole('link',{name:TITLE,exact:true}).waitFor();
const noReturn=await page.getByRole('button',{name:'Return Book',exact:true}).count()===0;
await page.getByText('Return this copy at the library desk. Staff will update your loan.',{exact:true}).waitFor();
await page.evaluate(async args=>{const r=await fetch('http://127.0.0.1:8001/borrows/'+args.loan+'/return',{method:'POST',headers:{Authorization:'Bearer '+args.token}});if(!r.ok)throw new Error('Staff return failed');},{loan:LOAN_ID,token:STAFF_TOKEN});
await page.getByRole('button',{name:'Refresh status',exact:true}).click();
await page.getByText('You currently have no borrowed books.',{exact:true}).waitFor();
await page.getByRole('button',{name:/Returned history/}).click();
await page.getByRole('link',{name:TITLE,exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/books?search='+encodeURIComponent(TITLE));
await page.getByRole('button',{name:'Visit library to borrow: '+TITLE,exact:true}).waitFor();
const noBorrow=await page.getByRole('button',{name:'Visit library to borrow: '+TITLE,exact:true}).isDisabled();
await page.getByLabel('Sort books',{exact:true}).selectOption('popular');
await page.goto('http://127.0.0.1:5174/books/'+BOOK_ID);
await page.getByLabel('Your Comments',{exact:true}).fill('Verified borrower review from an isolated acceptance fixture.');
await page.getByRole('button',{name:'Rate 4 stars',exact:true}).click();
await page.getByRole('button',{name:'Post Review',exact:true}).click();
await page.getByText('Your review has been successfully published!',{exact:true}).waitFor();
await page.reload();
await page.locator('p').filter({hasText:'Verified borrower review from an isolated acceptance fixture.'}).waitFor();
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));
return {url:page.url(),issuedLoanVisible:true,staffReturnSynced:true,noStudentReturn:noReturn,noStudentBorrow:noBorrow,verifiedReviewPersisted:true};
""".replace('STAFF_TOKEN',json.dumps(staff_token)).replace('TOKEN',json.dumps(token)).replace('TITLE',json.dumps(name)).replace('LOAN_ID',str(loan_id)).replace('BOOK_ID',str(bid))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55)
print(r.stdout);print(r.stderr);assert r.returncode==0
