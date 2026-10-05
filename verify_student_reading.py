import uuid,json,subprocess
from pypdf import PdfWriter
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User,UserRole
from app.models.digital_resource import DigitalResource
from app.models.reading_session import ReadingSession
from app.models.reader_state import ReaderState
from app.services.ebook_storage import PRIVATE_EBOOK_DIR
from app.services.auth import create_access_token
name=uuid.uuid4().hex+'.pdf';path=PRIVATE_EBOOK_DIR/name
writer=PdfWriter();writer.add_blank_page(width=600,height=800)
with path.open('wb') as f:writer.write(f)
rid=None
try:
 with SessionLocal() as db:
  user=db.query(User).filter(User.role==UserRole.STUDENT).first();token=create_access_token(user.id,user.role.value)
  resource=DigitalResource(title='Temporary reading verification',author='Test',file_url='/digital-resources/files/'+name,resource_type='uploaded_pdf',is_published=True,access_type='free');db.add(resource);db.commit();rid=resource.id
 program='''await page.goto('http://127.0.0.1:5173/login');await page.evaluate(t=>localStorage.setItem('bookbridge_token',t),TOKEN);await page.goto('http://127.0.0.1:5173/reader/RID');await page.getByText('Reading activity enabled.',{exact:false}).waitFor();const status=await page.getByText('Reading activity enabled.',{exact:false}).innerText();await page.goto('http://127.0.0.1:5173/dashboard');return {tracking:status};'''.replace('TOKEN',json.dumps(token)).replace('RID',str(rid))
 result=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-release','--session','student-reading-check-6p','browser','run','--stdin','--no-snapshot-diff','--timeout','35','-f','json'],input=program,text=True,capture_output=True,encoding='utf-8',timeout=45)
 print(result.stdout);print(result.stderr)
finally:
 if rid:
  with SessionLocal() as db:
   db.query(ReaderState).filter_by(resource_id=rid).delete();db.query(ReadingSession).filter_by(resource_id=rid).delete();db.query(DigitalResource).filter_by(id=rid).delete();db.commit()
 path.unlink(missing_ok=True)
