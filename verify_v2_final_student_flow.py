import json,subprocess,uuid,httpx
from pathlib import Path
import verification_v2_server as fixture
from app.services.auth import create_access_token
from app.models.contribution import XPTransaction
from app.models.reservation import Reservation
from app.models.book import Book
f=json.loads(Path('v2-integration-fixture.json').read_text());token=create_access_token(f['student'],'student');staff_token=create_access_token(f['staff'],'librarian')
program=r"""
await page.goto('http://127.0.0.1:5174/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);
await page.goto('http://127.0.0.1:5174/my-books?tab=reservations');await page.getByText('Pending — waiting for a copy',{exact:true}).waitFor();
await page.evaluate(async args=>{const r=await fetch('http://127.0.0.1:8001/borrows/'+args.loan+'/return',{method:'POST',headers:{Authorization:'Bearer '+args.token}});if(!r.ok)throw new Error('Return failed');},{loan:LOAN,token:STAFF});
await page.getByRole('button',{name:'Refresh status',exact:true}).click();await page.getByText('Ready for pickup',{exact:true}).waitFor();
await page.evaluate(async args=>{const r=await fetch('http://127.0.0.1:8001/admin/loans',{method:'POST',headers:{Authorization:'Bearer '+args.token,'Content-Type':'application/json'},body:JSON.stringify(args.payload)});if(!r.ok)throw new Error('Checkout failed');},{token:STAFF,payload:PAYLOAD});
await page.goto('http://127.0.0.1:5174/my-books');await page.getByRole('link',{name:TITLE,exact:true}).waitFor();
await page.goto('http://127.0.0.1:5174/my-books?tab=history');await page.getByText('Fulfilled — book issued',{exact:false}).waitFor();await page.reload();await page.getByText('Fulfilled — book issued',{exact:false}).waitFor();
await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));return {url:page.url(),pending:true,readyAfterStaffReturn:true,fulfilledAfterStaffIssue:true,historyReload:true};
""".replace('TOKEN',json.dumps(token)).replace('STAFF',json.dumps(staff_token)).replace('LOAN',str(f['initial_loan'])).replace('TITLE',json.dumps(f['title'])).replace('PAYLOAD',json.dumps({'student_id':f['student'],'book_id':f['book'],'request_id':str(uuid.uuid4())}))
r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','v2-circulation-checks-r5','browser','run','--stdin','--no-snapshot-diff','--timeout','45','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=55);print(r.stdout);print(r.stderr);assert r.returncode==0
client=httpx.Client(base_url='http://127.0.0.1:8001',timeout=30)
h={'Authorization':'Bearer '+token};sh={'Authorization':'Bearer '+staff_token}
with fixture.database.SessionLocal() as db:
 reservation=db.get(Reservation,f['reservation']);assert reservation.status=='fulfilled' and reservation.loan_id;loan=reservation.loan_id
r=client.post(f'/borrows/{loan}/return',headers=sh);assert r.status_code==200
r=client.post('/reviews/',headers=h,json={'book_id':f['book'],'rating':5,'comment':'Integrated verified borrower'});assert r.status_code==201,r.text
for kind in ['note','question_paper']:
 r=client.post('/student/contributions',headers=h,data={'request_key':str(uuid.uuid4()),'metadata':json.dumps({'title':'Integrated '+kind,'subject':'OS','kind':kind,'semester':5,'branch':'CSE'})},files={'file':('fixture.txt',b'Original academic fixture','text/plain')});assert r.status_code==201,r.text
 cid=r.json()['id'];decision={'decision':'APPROVED'} if kind=='note' else {'decision':'REJECTED','reason':'Please include the examination year.'}
 for _ in range(2):
  r=client.post(f'/admin/contributions/{cid}/decision',headers=sh,json=decision);assert r.status_code==200,r.text
with fixture.database.SessionLocal() as db:
 assert db.get(Book,f['book']).available_copies==1
 assert db.query(XPTransaction).filter_by(user_id=f['student'],event_type='QUIZ').count()==1
 assert sum(row.amount for row in db.query(XPTransaction).filter_by(user_id=f['student'],event_type='CONTRIBUTION'))==2
print('Same-student end-to-end integration passed: final inventory 1, preserved fulfilled loan link, review, quiz XP once, contribution XP exactly 2.')
