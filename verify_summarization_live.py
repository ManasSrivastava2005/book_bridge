"""Opt-in real local model browser test. Reads one existing student; no DB writes.
Run after model setup and API startup: python verify_summarization_live.py --browser-session SESSION
"""
import argparse
import json
from pathlib import Path
import subprocess
import httpx
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth import create_access_token
from test_book_summarization import TEXT, pdf_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-session', required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        assert student
        token = create_access_token(student.id, student.role.value)
    with httpx.Client(base_url='http://127.0.0.1:8000') as client:
        assert client.get('/health').status_code == 200
        assert client.post('/ai/summarize/text', json={'text':TEXT}).status_code == 401
        schema=client.get('/openapi.json').json()
        assert 'provider' in schema['components']['schemas']['SummaryResponse']['properties']
    program = r"""
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await context.grantPermissions(['clipboard-read', 'clipboard-write']);
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token => localStorage.setItem('bookbridge_token', token), TOKEN);
await page.goto('http://127.0.0.1:5173/ai?tab=summarize');
await page.getByRole('heading', {name:'Book Summarizer', exact:true}).waitFor();
await page.getByRole('textbox', {name:/Reading passage/}).fill(TEXT);
await page.getByRole('textbox', {name:/Title/}).fill('Operating Systems');
await page.getByRole('combobox', {name:'Summary type'}).selectOption('detailed');
const successPending=page.waitForResponse(r=>r.url().endsWith('/ai/summarize/text'));
await page.getByRole('button', {name:'Generate Summary',exact:true}).click();
await page.getByRole('status').filter({hasText:'Analyzing document locally'}).waitFor();
if(!(await page.getByRole('button',{name:'Generating summary…',exact:true}).isDisabled())) throw new Error('Duplicate generation not blocked');
const success = await successPending;
if(success.status()!==200) throw new Error('Text summary failed');
if(!(await success.request().allHeaders()).authorization?.startsWith('Bearer ')) throw new Error('JWT absent');
const body=await success.json();
if(body.provider!=='local' || body.model!=='google/flan-t5-base' || !body.summary)throw new Error('Local model response missing');
await page.getByRole('article', {name:'Generated summary'}).waitFor();
await page.getByRole('button',{name:'Copy',exact:true}).click();
await page.getByRole('button',{name:'Copied',exact:true}).waitFor();
const clipboard = await page.evaluate(()=>navigator.clipboard.readText());
if(clipboard.replace(/\r\n/g,'\n')!==body.summary.replace(/\r\n/g,'\n'))throw new Error('Copied summary differs');
if(await page.getByRole('button',{name:'Save to Notes',exact:true}).count())throw new Error('Student note action unexpectedly present');
await page.getByRole('button',{name:'Library Assistant',exact:true}).click();
await page.getByRole('textbox',{name:'',exact:true}).count();
await page.getByPlaceholder('Ask a question about library books, exam syllabus, programming concepts...').fill('find a book');
const chatPending=page.waitForResponse(r=>r.url().endsWith('/ai/chat'));
await page.getByRole('button',{name:'Send message',exact:true}).click();
const chat=await chatPending;
if(chat.status()!==200 || !(await chat.json()).response) throw new Error('Existing chat failed');
await page.getByRole('button',{name:'Book Summarizer',exact:true}).click();
await page.getByRole('article',{name:'Generated summary'}).waitFor();
await page.getByRole('button',{name:'Upload file',exact:true}).click();
await page.locator('input[type=file]').setInputFiles({name:'chapter.txt',mimeType:'text/plain',buffer:new TextEncoder().encode(TEXT)});
await page.getByRole('combobox',{name:'Summary type'}).selectOption('exam_notes');
const txtPending=page.waitForResponse(r=>r.url().endsWith('/ai/summarize/file'));
await page.getByRole('button',{name:'Generate Summary',exact:true}).click();
const txt = await txtPending;
if(txt.status()!==200 || (await txt.json()).mode!=='exam_notes')throw new Error('TXT request failed');
await page.getByRole('article',{name:'Generated summary'}).waitFor();
await page.locator('input[type=file]').setInputFiles({name:'chapter.pdf',mimeType:'application/pdf',buffer:new Uint8Array(PDF)});
await page.getByRole('combobox',{name:'Summary type'}).selectOption('key_points');
const pdfPending=page.waitForResponse(r=>r.url().endsWith('/ai/summarize/file'));
await page.getByRole('button',{name:'Generate Summary',exact:true}).click();
const pdf = await pdfPending;
if(pdf.status()!==200 || (await pdf.json()).mode!=='key_points')throw new Error('PDF request failed');
await page.getByRole('article',{name:'Generated summary'}).waitFor();
await page.locator('input[type=file]').setInputFiles({name:'bad.exe',mimeType:'application/octet-stream',buffer:new TextEncoder().encode(TEXT)});
await page.getByRole('button',{name:'Generate Summary',exact:true}).click();
await page.getByRole('alert').filter({hasText:'Upload a PDF or TXT file.'}).waitFor();
const downloadPending=page.waitForEvent('download');
await page.getByRole('button',{name:'Download',exact:true}).click();
if((await downloadPending).suggestedFilename()!=='book-bridge-summary.txt')throw new Error('Download failed');
await page.setViewportSize({width:390,height:844});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Mobile horizontal overflow');
await page.getByRole('button',{name:'Paste text',exact:true}).click();
if(await page.getByRole('textbox',{name:/Reading passage/}).inputValue()!==TEXT)throw new Error('Text lost when switching sources');
if(errors.length)throw new Error(errors.join('; '));
await page.evaluate(()=>{localStorage.removeItem('bookbridge_token');localStorage.removeItem('bookbridge_user');});
await page.goto('http://127.0.0.1:5173/login');
return {page:'Book Summarizer',jwt:true,loading:true,text:true,txt:true,pdf:true,invalidFile:true,copy:true,download:true,noStudentSaveToNotes:true,chatPreserved:true,tabStatePreserved:true,mobile:true,pageErrors:errors,provider:'local FLAN-T5 Base'};
"""
    constants = '\n'.join(f'const {key}={json.dumps(value)};' for key,value in {'TOKEN':token,'TEXT':TEXT,'PDF':list(pdf_bytes())}.items())
    command = [str(Path.home()/'AppData/Roaming/npm/webcmd.cmd'),'--profile','bookbridge-notes','--session',args.browser_session,'browser','run','--stdin','--timeout','55','--no-snapshot-diff']
    result = subprocess.run(command,input=constants+program,text=True,capture_output=True,encoding='utf-8',timeout=65)
    print((result.stdout+result.stderr).replace(token,'[redacted]')[:6000])
    assert result.returncode == 0, 'Browser verification failed'


if __name__ == '__main__':
    main()
