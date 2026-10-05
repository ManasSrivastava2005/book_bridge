"""Real PDF/browser/PostgreSQL reader check; removes only its own fixtures."""
import argparse
import json
from pathlib import Path
import subprocess
import uuid
import httpx
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from app.models.digital_resource import DigitalResource
from app.models.reader_state import ReaderState
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.library import Library
from app.services.auth import create_access_token

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--browser-session',required=True)
args=parser.parse_args()
with SessionLocal() as db:
 user=db.query(User).filter(User.role==UserRole.STUDENT).first()
 assert user
 token=create_access_token(user.id,user.role.value); uid=user.id
program=r'''
const errors=[];
page.on('pageerror',e=>errors.push(e.message));
const sync=async()=>{await page.getByRole('status').filter({hasText:'Synced to your account.'}).waitFor();};
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(({token,uid,id})=>{
 localStorage.setItem('bookbridge_token',token);
 localStorage.setItem(`bookbridge:reader:v1:${uid}:${id}`,JSON.stringify({page:1,bookmarks:[{page:1,note:'Older bookmark'}]}));
},{token:TOKEN,uid:UID,id:IDS[0]});
await page.goto('http://127.0.0.1:5173/reader/'+IDS[0]);
await page.getByRole('heading',{name:TITLE,exact:true}).waitFor();
await page.locator('.react-pdf__Page canvas').waitFor();
await page.getByText('of 3',{exact:true}).waitFor();
await sync();
await page.getByRole('button',{name:'Import older browser bookmarks',exact:true}).click();
await page.getByRole('list',{name:'Bookmarks',exact:true}).getByText('Older bookmark',{exact:true}).waitFor();
await sync();
await page.getByRole('button',{name:'Next page',exact:true}).click();
await page.getByLabel('Note for page 2',{exact:true}).waitFor();
await page.locator('.react-pdf__Page[data-page-number="2"] canvas').waitFor();
await sync();
await page.getByLabel('Note for page 2',{exact:true}).fill('Review virtual memory.');
await page.getByRole('button',{name:'Add bookmark',exact:true}).click();
await page.getByRole('list',{name:'Bookmarks',exact:true}).getByText('Review virtual memory.',{exact:true}).waitFor();
await sync();
await page.locator('.react-pdf__Page__textContent span').filter({hasText:'Page two covers memory management.'}).waitFor();
await page.evaluate(()=>{
 const span=Array.from(document.querySelectorAll('.react-pdf__Page__textContent span')).find(e=>e.textContent.includes('Page two covers memory management.'));
 const range=document.createRange();range.selectNodeContents(span);
 const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
 span.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));
});
await page.getByRole('button',{name:'Save highlight',exact:true}).click();
await page.getByRole('list',{name:'Highlights',exact:true}).getByRole('blockquote').waitFor();
await sync();
await page.getByRole('textbox',{name:/Highlight note /}).fill('Important exam concept.');
await page.getByRole('button',{name:'Save highlight note',exact:true}).click();
await sync();
await page.getByRole('combobox',{name:'Reading theme',exact:true}).selectOption('sepia');
await sync();
await page.getByRole('combobox',{name:'Zoom',exact:true}).selectOption('125');
if(!(await page.locator('[data-reader-highlight]').count()))throw new Error('Highlight overlay absent');
await page.evaluate(({uid,id})=>localStorage.removeItem(`bookbridge:reader:v1:${uid}:${id}`),{uid:UID,id:IDS[0]});
await page.reload();
await page.locator('.react-pdf__Page[data-page-number="2"] canvas').waitFor();
await sync();
if(await page.getByLabel('Page',{exact:true}).inputValue()!=='2')throw new Error('Server progress not restored');
if(await page.getByLabel('Note for page 2',{exact:true}).inputValue()!=='Review virtual memory.')throw new Error('Server bookmark not restored');
if(await page.getByRole('textbox',{name:/Highlight note /}).inputValue()!=='Important exam concept.')throw new Error('Server highlight note not restored');
if(await page.getByRole('combobox',{name:'Reading theme',exact:true}).inputValue()!=='sepia')throw new Error('Theme not restored');
await page.getByText('Chapters',{exact:true}).click();
await page.getByRole('link',{name:'Chapter three',exact:true}).click();
await page.locator('.react-pdf__Page[data-page-number="3"] canvas').waitFor();
await sync();
await page.setViewportSize({width:390,height:844});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');
await page.getByRole('button',{name:'Page 2',exact:true}).click();
await sync();
await page.getByRole('button',{name:'Remove bookmark for page 2',exact:true}).click();
await sync();
await page.getByRole('button',{name:/Remove highlight /}).click();
await sync();
if(await page.locator('[data-reader-highlight]').count())throw new Error('Highlight not removed');
const endpoint='http://127.0.0.1:8000/reader/'+IDS[0]+'/state';
const otherState=await (await page.request.get(endpoint,{headers:{Authorization:'Bearer '+TOKEN}})).json();
const otherSave=await page.request.put(endpoint,{headers:{Authorization:'Bearer '+TOKEN},data:{...otherState,theme:'dark'}});
if(otherSave.status()!==200)throw new Error('Second-session save failed');
await page.getByRole('combobox',{name:'Reading theme',exact:true}).selectOption('light');
await page.getByRole('alert').filter({hasText:'Reading data changed in another session'}).waitFor();
await page.getByRole('button',{name:'Reload saved data',exact:true}).click();
await page.locator('.react-pdf__Page[data-page-number="2"] canvas').waitFor();
await sync();
if(await page.getByRole('combobox',{name:'Reading theme',exact:true}).inputValue()!=='dark')throw new Error('Newer server save was overwritten');
await page.goto('http://127.0.0.1:5173/reader/'+IDS[1]);
await page.locator('.react-pdf__Page[data-page-number="1"] canvas').waitFor();
await sync();
if(await page.getByLabel('Page',{exact:true}).inputValue()!=='1')throw new Error('Document state leaked');
await page.goto('http://127.0.0.1:5173/reader/'+IDS[2]);
await page.getByRole('alert').filter({hasText:'no readable file'}).waitFor();
await page.goto('http://127.0.0.1:5173/reader/'+IDS[3]);
await page.getByRole('alert').filter({hasText:'no readable file'}).waitFor();
await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_user');});
await page.goto('http://127.0.0.1:5173/login');
if(errors.length)throw new Error(errors.join('; '));
return {realPdfCanvas:true,actualPageCount:3,automaticResume:true,legacyBookmarkImport:true,bookmarkCreateRemove:true,highlightCreateNoteRemove:true,serverPersistenceWithoutLocalStorage:true,chapterNavigation:true,theme:true,zoom:true,mobile:true,documentIsolation:true,missingAndUnsafeUrls:true,concurrentSessionConflict:true,pageErrors:errors};
'''
fixture=Path('uploads/ebooks')/f'reader-verification-{uuid.uuid4().hex}.pdf'
fixture.parent.mkdir(parents=True,exist_ok=True)
writer=PdfWriter()
for content in ['Page one introduces operating systems.','Page two covers memory management.','Page three covers process scheduling.']:
 page=writer.add_blank_page(width=612,height=792)
 font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
 page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
 stream=DecodedStreamObject();stream.set_data(f'BT /F1 14 Tf 40 700 Td ({content}) Tj ET'.encode())
 page[NameObject('/Contents')]=writer._add_object(stream)
writer.add_outline_item('Chapter three',2)
with fixture.open('wb') as out:writer.write(out)
ids=[];title=f'Reader verification {uuid.uuid4().hex[:8]}'
try:
 with SessionLocal() as db:
  for i in range(4):
   row=DigitalResource(title=title,author='Verification fixture',provider='Book Bridge',resource_type='uploaded_pdf',file_url='/'+fixture.as_posix() if i<2 else (None if i==2 else 'javascript:alert(1)'),uploaded_by=uid,is_published=True)
   db.add(row);db.flush();ids.append(row.id)
  db.commit()
 constants='\n'.join(f'const {k}={json.dumps(v)};' for k,v in {'TOKEN':token,'UID':uid,'IDS':ids,'TITLE':title}.items())+'\n'
 command=[str(Path.home()/'AppData/Roaming/npm/webcmd.cmd'),'--profile','bookbridge-notes','--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff']
 result=subprocess.run(command,input=constants+program,text=True,capture_output=True,encoding='utf-8',timeout=65)
 print((result.stdout+result.stderr).replace(token,'[redacted]')[:6500])
 assert result.returncode==0,'Browser reader verification failed'
 with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+token}) as client:
  state=client.get(f'/reader/{ids[0]}/state').json()
  assert state['page']==2 and state['theme']=='dark' and state['highlights']==[]
  assert state['bookmarks']==[{'page':1,'note':'Older bookmark'}]
  assert client.put(f'/reader/{ids[0]}/state',json={**state,'version':0}).status_code==409
 print('Independent HTTP client confirms PostgreSQL persistence and stale-save rejection.')
finally:
 with SessionLocal() as db:
  if ids:
   db.query(ReaderState).filter(ReaderState.resource_id.in_(ids)).delete(synchronize_session=False)
   db.query(DigitalResource).filter(DigitalResource.id.in_(ids),DigitalResource.title==title).delete(synchronize_session=False)
   db.commit()
 fixture.unlink(missing_ok=True)
