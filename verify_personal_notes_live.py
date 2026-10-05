"""Opt-in personal Notes UI and PostgreSQL verification; cleans only its own fixtures."""
import argparse
import json
from pathlib import Path
import subprocess
import uuid
import httpx
from app.database import SessionLocal
from app.models.library import Library
from app.models.user import User, UserRole
from app.models.note import Note
from app.routers.notes import PRIVATE_UPLOAD_DIR
from app.services.auth import create_access_token

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--browser-session', required=True)
args = parser.parse_args()
marker = 'Personal notes verification ' + uuid.uuid4().hex[:10]
with SessionLocal() as db:
    student = db.query(User).filter(User.role == UserRole.STUDENT).first()
    other = db.query(User).filter(User.id != student.id).first()
    token = create_access_token(student.id, student.role.value)
    other_token = create_access_token(other.id, other.role.value)
program = r'''
const errors=[]; page.on('pageerror', e=>errors.push(e.message));
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token=>localStorage.setItem('bookbridge_token',token), TOKEN);
await page.goto('http://127.0.0.1:5173/notes');
await page.getByRole('heading',{name:'Notes Library & Lecture Summaries'}).waitFor();
await page.getByRole('button',{name:'Upload your own notes',exact:true}).click();
await page.getByLabel('Document Title *',{exact:true}).fill(MARKER);
await page.locator('#note-file').setInputFiles({name:'my-notes.txt',mimeType:'text/plain',buffer:new TextEncoder().encode('Private study verification')});
const pending=page.waitForResponse(r=>r.url().endsWith('/notes/my/upload') && r.request().method()==='POST');
await page.getByRole('button',{name:'Upload private note',exact:true}).click();
if((await pending).status()!==201)throw new Error('Personal upload failed');
await page.getByRole('heading',{name:MARKER,exact:true}).waitFor();
await page.reload();
await page.getByRole('button',{name:'My notes',exact:true}).click();
await page.getByRole('heading',{name:MARKER,exact:true}).waitFor();
const file=page.waitForResponse(r=>r.url().includes('/notes/personal-files/') && r.request().method()==='GET');
await page.getByRole('link',{name:'Download '+MARKER,exact:true}).click();
const downloaded=await file;
if(downloaded.status()!==200 || await downloaded.text()!=='Private study verification')throw new Error('Download mismatch');
await page.setViewportSize({width:390,height:844});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');
await page.getByRole('button',{name:'Library notes',exact:true}).click();
await page.getByRole('button',{name:'My notes',exact:true}).click();
await page.getByRole('heading',{name:MARKER,exact:true}).waitFor();
await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_user');});
await page.goto('http://127.0.0.1:5173/login');
if(errors.length)throw new Error(errors.join(';'));
return {studentUpload:true,reloadPersistence:true,authenticatedDownload:true,mobile:true,pageErrors:errors};
'''
try:
    constants='const TOKEN='+json.dumps(token)+'; const MARKER='+json.dumps(marker)+';\n'
    result=subprocess.run([r'C:\Users\manas\AppData\Roaming\npm\webcmd.cmd','--profile','bookbridge-notes','--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff'],input=constants+program,capture_output=True,text=True,encoding='utf-8',timeout=65)
    print(result.stdout.replace(token,'[redacted]').replace(other_token,'[redacted]'))
    if result.returncode:
        print(result.stderr.replace(token,'[redacted]')); raise RuntimeError('Browser verification failed')
    with SessionLocal() as db:
        note=db.query(Note).filter(Note.title==marker).one()
        note_id=note.id; url=note.file_url
        assert note.status=='personal' and note.access_level=='private'
    with httpx.Client(base_url='http://127.0.0.1:8000') as client:
        assert client.get(url).status_code==401
        assert client.get(url,headers={'Authorization':'Bearer '+other_token}).status_code==404
        assert client.get('/notes/'+str(note_id)).status_code==404
        assert all(n['id']!=note_id for n in client.get('/notes/').json())
        assert client.get('/search/unified',params={'query':marker}).json()['notes']==[]
        assert client.get(url,headers={'Authorization':'Bearer '+token}).content==b'Private study verification'
    print('PostgreSQL ownership, anonymous/other-user denial, public catalog and search isolation: passed')
finally:
    with SessionLocal() as db:
        rows=db.query(Note).filter(Note.title==marker).all()
        paths=[Path(PRIVATE_UPLOAD_DIR)/Path(n.file_url).name for n in rows]
        for row in rows: db.delete(row)
        db.commit()
        for path in paths: path.unlink(missing_ok=True)
