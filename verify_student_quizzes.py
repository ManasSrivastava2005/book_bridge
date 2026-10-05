import uuid,json,subprocess
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User,UserRole
from app.models.book import Book
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.quiz import Quiz,QuizQuestion
from app.models.quiz_attempt import QuizAttempt
from app.models.badge import UserBadge
from app.models.contribution import XPTransaction
from app.services.auth import create_access_token
uid=qid=None
try:
 with SessionLocal() as db:
  staff=db.query(User).filter(User.role==UserRole.LIBRARIAN).first();book=db.query(Book).first()
  u=User(name='Quiz verification',email=uuid.uuid4().hex+'@example.com',hashed_password='unusable',role=UserRole.STUDENT);db.add(u);db.flush();uid=u.id
  q=Quiz(title='Verification chapter quiz',book_id=book.id,chapter='Test chapter',created_by=staff.id,status='published',active=True,permission_confirmed=True);db.add(q);db.flush();qid=q.id
  for i in range(10):db.add(QuizQuestion(quiz_id=q.id,position=i,prompt=f'Fixture question {i+1}',options=['Correct fixture answer','Other fixture answer'],correct_index=0,explanation='Fixture explanation'))
  db.commit();token=create_access_token(uid,'student')
 program="""await page.goto('http://127.0.0.1:5173/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5173/quizzes?quiz=QID');await page.getByRole('radio',{name:'Correct fixture answer',exact:true}).first().waitFor();for(let i=0;i<10;i++)await page.getByRole('radio',{name:'Correct fixture answer',exact:true}).nth(i).click();await page.getByRole('button',{name:'Submit answers'}).click();await page.getByText('Score: 100%',{exact:true}).waitFor();const score=await page.getByText('Score: 100%',{exact:true}).innerText();await page.evaluate(()=>localStorage.removeItem('bookbridge_token'));await page.goto('http://127.0.0.1:5173/login');return {score};""".replace('TOKEN',json.dumps(token)).replace('QID',str(qid))
 r=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','student-plan-verification-vt','browser','run','--stdin','--no-snapshot-diff','--timeout','35','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=45);print(r.stdout);print(r.stderr)
 with SessionLocal() as db:print({'persisted_attempts':db.query(QuizAttempt).filter_by(user_id=uid,score=100).count(),'quiz_xp':sum(r.amount for r in db.query(XPTransaction).filter_by(user_id=uid))})
finally:
 with SessionLocal() as db:
  if uid:
   for model in (UserBadge,XPTransaction,QuizAttempt):db.query(model).filter_by(user_id=uid).delete()
  if qid:db.query(QuizQuestion).filter_by(quiz_id=qid).delete();db.query(Quiz).filter_by(id=qid).delete()
  if uid:db.query(User).filter_by(id=uid).delete()
  db.commit()
