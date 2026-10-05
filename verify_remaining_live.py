"""Combined live checks; only unique test resources/rooms/files are removed."""
import argparse,io,json,subprocess,uuid
from pathlib import Path
from pypdf import PdfWriter
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User,UserRole
from app.models.digital_resource import DigitalResource
from app.models.reader_state import ReaderState
from app.models.study import StudyRoom,StudyMember,StudyMessage,StudyAudit,StudyReport,StudyAttachment
from app.models.notification import Notification
from app.services.auth import create_access_token
from app.services.ebook_storage import PRIVATE_EBOOK_DIR
from app.routers.study import ATTACHMENT_DIR
parser=argparse.ArgumentParser();parser.add_argument('--browser-session',required=True);parser.add_argument('--browser-profile',default='bookbridge-notes');args=parser.parse_args()
marker='Remaining verification '+uuid.uuid4().hex[:8]
writer=PdfWriter();writer.add_blank_page(width=300,height=400);stream=io.BytesIO();writer.write(stream)
with SessionLocal() as db:
 staff=db.query(User).filter(User.role.in_([UserRole.LIBRARIAN,UserRole.ADMIN])).first()
 students=db.query(User).filter(User.role==UserRole.STUDENT).order_by(User.id).limit(2).all()
 assert staff and len(students)==2
 tokens=[create_access_token(u.id,u.role.value) for u in [staff,*students]]
program=r'''
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),STAFF);
await page.goto('http://127.0.0.1:5173/admin/resources');
await page.getByRole('heading',{name:'Manage digital resources',exact:true}).waitFor();
await page.getByLabel('Title',{exact:true}).fill(MARKER+' PDF');
await page.getByLabel('Author',{exact:true}).fill('Verification fixture');
await page.locator('input[type=file]').setInputFiles({name:'verification.pdf',mimeType:'application/pdf',buffer:new Uint8Array(PDF)});
const upload=page.waitForResponse(r=>r.url().endsWith('/digital-resources/upload') && r.request().method()==='POST');
await page.getByRole('button',{name:'Save resource',exact:true}).click();
const uploaded=await upload;if(uploaded.status()!==201)throw new Error('PDF upload failed');
const resource=await uploaded.json();
await page.getByRole('status').filter({hasText:'Digital resource saved.'}).waitFor();
await page.goto('http://127.0.0.1:5173/reader/'+resource.id);
await page.locator('.react-pdf__Page canvas').waitFor();
await page.goto('http://127.0.0.1:5173/admin/resources');
await page.getByRole('textbox',{name:'Search digital resources',exact:true}).fill(MARKER+' PDF');
const article=page.getByRole('article').filter({hasText:MARKER+' PDF'});
await article.getByRole('button',{name:'Publish',exact:true}).click();
await article.getByText('Published',{exact:true}).waitFor();
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),OWNER);
await page.goto('http://127.0.0.1:5173/reader/'+resource.id);
await page.locator('.react-pdf__Page canvas').waitFor();
const downloaded=page.waitForEvent('download');
await page.getByRole('button',{name:'Download PDF',exact:true}).click();
await (await downloaded).saveAs('verified-private-pdf.pdf');
await page.goto('http://127.0.0.1:5173/study-together');
await page.getByText('Create a study room',{exact:true}).click();
await page.getByLabel('Room title',{exact:true}).fill(MARKER);
await page.getByLabel('Subject',{exact:true}).fill('Verification');
await page.getByLabel('Invitation-only room',{exact:true}).check();
await page.getByRole('button',{name:'Create room',exact:true}).click();
await page.getByRole('heading',{name:MARKER,exact:true}).waitFor();
const invite=await page.getByRole('textbox',{name:'Invitation link',exact:true}).inputValue();
const roomId=page.url().split('/').pop();
await page.getByLabel('Your message',{exact:true}).fill('Owner fixture message');
await page.getByRole('button',{name:'Post message',exact:true}).click();
await page.getByText('Owner fixture message',{exact:true}).waitFor();
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),MEMBER);
await page.goto('http://127.0.0.1:5173/study-together/'+roomId);
await page.getByRole('alert').filter({hasText:'Study room not found'}).waitFor();
await page.goto(invite);
await page.getByRole('button',{name:'Join room',exact:true}).click();
await page.getByText('Owner fixture message',{exact:true}).waitFor();
await page.getByLabel('Room attachment',{exact:true}).setInputFiles({name:'study.txt',mimeType:'text/plain',buffer:new TextEncoder().encode('Shared fixture bytes')});
await page.getByRole('button',{name:'Upload shared file',exact:true}).click();
await page.getByText('study.txt · 1 KB',{exact:true}).waitFor();
const attachment=page.waitForEvent('download');
await page.getByRole('button',{name:'Download file',exact:true}).click();
await (await attachment).saveAs('verified-room-file.txt');
await page.getByRole('article').filter({hasText:'Owner fixture message'}).getByRole('button',{name:'Report message',exact:true}).click();
await page.getByLabel('Reason for report',{exact:true}).fill(MARKER+' report');
await page.getByRole('button',{name:'Submit report',exact:true}).click();
await page.getByRole('status').filter({hasText:'Report sent'}).waitFor();
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),OWNER);
await page.goto('http://127.0.0.1:5173/study-together/'+roomId);
await page.getByText('Owner fixture message',{exact:true}).waitFor();
const posted=await page.request.post('http://127.0.0.1:8000/study/rooms/'+roomId+'/messages',{headers:{Authorization:'Bearer '+MEMBER},data:{body:'Automatic update fixture',client_id:MESSAGE_ID}});
if(posted.status()!==201)throw new Error('Peer post failed');
await page.getByText('Automatic update fixture',{exact:true}).waitFor({timeout:18000});
await page.setViewportSize({width:390,height:844});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Room mobile overflow');
await page.goto('http://127.0.0.1:5173/notifications');
const notice=page.getByRole('article').filter({hasText:'New discussion in Study Together: '+MARKER});
await notice.waitFor();
await notice.getByRole('button',{name:'Mark as read',exact:true}).click();
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token),STAFF);
await page.goto('http://127.0.0.1:5173/admin/study-moderation');
const report=page.getByRole('article').filter({hasText:MARKER+' report'});
await report.getByRole('button',{name:'Resolve report',exact:true}).click();
await page.getByRole('heading',{name:'Audit log',exact:true}).waitFor();
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Moderation mobile overflow');
await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_user');});
await page.goto('http://127.0.0.1:5173/login');
if(errors.length)throw new Error(errors.join(';'));
return {privatePdfUpload:true,staffDraftPreview:true,studentPdfRender:true,pdfDownload:true,invitationIsolation:true,inviteJoin:true,attachmentUploadDownload:true,reportAndResolution:true,automaticDiscussionUpdate:true,notificationRead:true,mobile:true,pageErrors:errors};
'''
try:
 constants='\n'.join('const '+key+'='+json.dumps(value)+';' for key,value in {'STAFF':tokens[0],'OWNER':tokens[1],'MEMBER':tokens[2],'MARKER':marker,'PDF':list(stream.getvalue()),'MESSAGE_ID':str(uuid.uuid4())}.items())+'\n'
 result=subprocess.run([str(Path.home()/'AppData/Roaming/npm/webcmd.cmd'),'--profile',args.browser_profile,'--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff'],input=constants+program,text=True,capture_output=True,encoding='utf-8',timeout=65)
 output=result.stdout+result.stderr
 for token in tokens:output=output.replace(token,'[redacted]')
 print(output);assert result.returncode==0,'Browser verification failed'
 receipt=json.loads(result.stdout);assert receipt['ok']
 for artifact in receipt['artifacts']:
  path=Path.home()/'.webcmd/cache/browser-run'/artifact['artifactId']/artifact['filename']
  if artifact['filename']=='verified-private-pdf.pdf':assert path.read_bytes()==stream.getvalue()
  if artifact['filename']=='verified-room-file.txt':assert path.read_bytes()==b'Shared fixture bytes'
 with SessionLocal() as db:
  room=db.query(StudyRoom).filter(StudyRoom.title==marker).one()
  assert room.is_private
  assert db.query(StudyReport).filter(StudyReport.room_id==room.id,StudyReport.resolved==True).count()==1
  assert db.query(StudyAudit).filter(StudyAudit.room_id==room.id,StudyAudit.action=='resolve_report').count()==1
 print('Downloaded PDF/attachment bytes and persisted private-room moderation verified.')
finally:
 with SessionLocal() as db:
  rooms=db.query(StudyRoom).filter(StudyRoom.title==marker).all()
  for room in rooms:
   for item in db.query(StudyAttachment).filter(StudyAttachment.room_id==room.id).all():(ATTACHMENT_DIR/item.storage_name).unlink(missing_ok=True)
   for model in (StudyReport,StudyAttachment,StudyAudit,StudyMessage,StudyMember):db.query(model).filter(model.room_id==room.id).delete(synchronize_session=False)
   db.delete(room)
  for resource in db.query(DigitalResource).filter(DigitalResource.title==marker+' PDF').all():
   if resource.file_url and resource.file_url.startswith('/digital-resources/files/'):(PRIVATE_EBOOK_DIR/resource.file_url.rsplit('/',1)[-1]).unlink(missing_ok=True)
   db.query(ReaderState).filter(ReaderState.resource_id==resource.id).delete(synchronize_session=False)
   db.delete(resource)
  db.query(Notification).filter(Notification.message=='New discussion in Study Together: '+marker).delete(synchronize_session=False)
  db.commit()
