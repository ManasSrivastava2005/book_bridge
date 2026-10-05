"""Opt-in Notes check against the running local PostgreSQL-backed application.

Run after starting uvicorn and Vite:
  python verify_notes_live.py --browser-session SESSION_ID
Uses existing staff/student identities with application-issued JWTs, without
changing accounts or logging credentials. Only notes created by this run are
removed. Requires the local webcmd browser session specified below.
"""

import argparse
import json
from pathlib import Path
import subprocess
import uuid

import httpx
from sqlalchemy import inspect

from app.database import SessionLocal, engine
from app.models.library import Library  # Registers User.library relationship.
from app.models.note import Note
from app.models.user import User, UserRole
from app.services.auth import create_access_token


ROOT = Path(__file__).resolve().parent
API = "http://127.0.0.1:8000"
MARKER = f"Notes verification {uuid.uuid4().hex}"
CONTENT = "Book Bridge verification: normalization reduces redundant data.\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-session", required=True)
    parser.add_argument("--browser-profile", default="bookbridge-notes")
    args = parser.parse_args()
    assert engine.url.get_backend_name() == "postgresql"
    assert engine.url.database == "bookbridge_v2"
    assert set(Note.__table__.columns.keys()) <= {
        column["name"] for column in inspect(engine).get_columns("notes")
    }
    with SessionLocal() as db:
        staff = db.query(User).filter(User.role == UserRole.LIBRARIAN).first()
        student = db.query(User).filter(User.role == UserRole.STUDENT).first()
        assert staff is not None and student is not None, "Existing test roles required"
        staff_token = create_access_token(staff.id, staff.role.value)
        student_token = create_access_token(student.id, student.role.value)
        before_count = db.query(Note).count()
    results = {}
    try:
        with httpx.Client(base_url=API, timeout=45) as client:
            for label, token in (("staff", staff_token), ("student", student_token)):
                profile = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
                assert profile.status_code == 200
                results[f"{label}_jwt"] = profile.status_code
            for path in ("/health", "/books/", "/libraries/", "/digital-resources/",
                         "/question-banks/", "/notes/", "/search/unified?query=python"):
                response = client.get(path)
                assert response.status_code == 200, (path, response.status_code)
                results[path] = response.status_code
            cors = client.options("/notes/upload", headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            })
            assert cors.status_code == 200
            assert cors.headers.get("access-control-allow-origin") in (
                "*", "http://127.0.0.1:5173")
            results["cors"] = "passed"
            fields = {"title": MARKER, "subject": "DBMS", "semester": "5"}
            for label, headers, expected in (
                ("anonymous", {}, 401),
                ("student", {"Authorization": f"Bearer {student_token}"}, 403),
            ):
                rejected = client.post("/notes/upload", data=fields,
                    files={"file": ("verification.txt", CONTENT.encode(), "text/plain")},
                    headers=headers)
                assert rejected.status_code == expected
                results[f"{label}_upload"] = expected

        program = """
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await page.unroute('**/notes/upload');
await page.goto('http://127.0.0.1:5173/login');
await page.evaluate(token => localStorage.setItem('bookbridge_token', token), STAFF_TOKEN);
await page.goto('http://127.0.0.1:5173/notes');
await page.getByRole('heading', {name: 'Notes Library & Lecture Summaries'}).waitFor();
await page.getByRole('button', {name: 'Upload Study Material', exact: true}).click();
await page.getByLabel('Document Title *', {exact: true}).fill(MARKER);
await page.getByLabel('Subject *', {exact: true}).fill('DBMS');
await page.getByLabel('Semester', {exact: true}).selectOption('5');
await page.locator('#note-file').setInputFiles({name: 'notes-verification.txt',
    mimeType: 'text/plain', buffer: new TextEncoder().encode(CONTENT)});
const uploadPending = page.waitForResponse(r => r.url().endsWith('/notes/upload') && r.request().method() === 'POST');
await page.getByRole('button', {name: 'Publish Note', exact: true}).click();
const upload = await uploadPending;
if (upload.status() !== 201) throw new Error('Upload failed: ' + upload.status() + ' ' + await upload.text());
const note = await upload.json();
await page.getByRole('heading', {name: MARKER, exact: true}).waitFor();
const immediate = await page.getByRole('status').textContent();
await page.reload();
await page.getByRole('heading', {name: MARKER, exact: true}).waitFor();
const trackingPending = page.waitForResponse(r => r.url().endsWith('/notes/' + note.id + '/download'));
const popupPending = context.waitForEvent('page');
await page.getByRole('link', {name: 'Download ' + MARKER, exact: true}).click();
const tracked = await trackingPending;
const tracking = await tracked.json();
const popup = await popupPending;
await popup.waitForLoadState('domcontentloaded');
const downloadedText = await popup.locator('body').innerText();
if (downloadedText.trim() !== CONTENT.trim()) throw new Error('Downloaded content mismatch');
await page.getByRole('heading', {name: MARKER, exact: true}).locator('..').getByText('1 downloads', {exact: true}).waitFor();
await page.getByRole('button', {name: 'Upload Study Material', exact: true}).click();
await page.locator('#note-file').setInputFiles({name:'unsupported.exe', mimeType:'application/octet-stream', buffer:new TextEncoder().encode('rejected')});
await page.getByRole('alert').filter({hasText:'Unsupported file type'}).waitFor();
await page.locator('#note-file').setInputFiles({name:'empty.txt', mimeType:'text/plain', buffer:new Uint8Array(0)});
await page.getByRole('alert').filter({hasText:'empty'}).waitFor();
await page.getByLabel('Document Title *', {exact: true}).fill(MARKER);
await page.locator('#note-file').setInputFiles({name:'error-check.txt', mimeType:'text/plain', buffer:new TextEncoder().encode(CONTENT)});
// Deliberately send invalid multipart metadata through the existing client to
// verify the real FastAPI validation-array response without writing a record.
const interceptorId = await page.evaluate(async () => {
  const {default: api} = await import('/src/services/api.ts');
  return api.interceptors.request.use(config => {
    if (config.url === '/notes/upload' && config.data instanceof FormData) config.data.set('semester', 'invalid');
    return config;
  });
});
await page.getByRole('button', {name:'Publish Note',exact:true}).click();
await page.getByRole('alert').filter({hasText:'Input should be a valid integer'}).waitFor();
await page.evaluate(async id => {
  const {default: api} = await import('/src/services/api.ts');
  api.interceptors.request.eject(id);
}, interceptorId);
await page.getByRole('button', {name:'Close upload dialog',exact:true}).click();
await page.evaluate(token => localStorage.setItem('bookbridge_token', token), STUDENT_TOKEN);
await page.goto('http://127.0.0.1:5173/notes');
await page.getByRole('heading', {name: MARKER, exact: true}).waitFor();
const studentUploadControls = await page.getByRole('button', {name:'Upload Study Material',exact:true}).count();
if (studentUploadControls !== 0) throw new Error('Student upload controls exposed');
if (errors.length) throw new Error('Browser errors: ' + errors.join('; '));
return {noteId: note.id, fileUrl: note.file_url, uploadStatus: upload.status(),
 immediateDisplay: immediate.includes('successfully'), reload: true,
 downloadContent: true, tracking, studentUploadControls,
 clientValidation: true, validationArrayDisplayed: true, pageErrors: errors};
"""
        # Session material stays in process memory and the application's own
        # browser storage. It is never written into scripts, logs, or reports.
        constants = "\n".join(f"const {name} = {json.dumps(value)};" for name, value in {
            "STAFF_TOKEN": staff_token, "STUDENT_TOKEN": student_token,
            "MARKER": MARKER, "CONTENT": CONTENT,
        }.items())
        command = [str(Path.home() / "AppData/Roaming/npm/webcmd.cmd"),
            "--profile", args.browser_profile, "--session", args.browser_session,
            "browser", "run", "--stdin", "--timeout", "55", "--no-snapshot-diff"]
        browser = subprocess.run(command, input=constants + program, text=True,
                                 capture_output=True, timeout=65, encoding="utf-8")
        if browser.returncode:
            safe_output = (browser.stdout + browser.stderr).replace(staff_token, "[redacted]").replace(student_token, "[redacted]")
            raise AssertionError(safe_output[:4000])
        browser_result = json.loads(browser.stdout)
        print(json.dumps({"browser": browser_result}, ensure_ascii=True))
        with SessionLocal() as db:
            note = db.query(Note).filter(Note.title == MARKER).one()
            stored = (ROOT / note.file_url.lstrip("/")).resolve()
            assert stored.parent == (ROOT / "uploads/notes").resolve()
            assert stored.read_text(encoding="utf-8") == CONTENT
            assert note.download_count == 1
            results["postgresql_metadata_and_count"] = "passed"
            results["physical_file_content"] = "passed"
        print(json.dumps({"live_checks": results}, ensure_ascii=True))
    finally:
        with SessionLocal() as db:
            created = db.query(Note).filter(Note.title == MARKER).all()
            paths = [ROOT / note.file_url.lstrip("/") for note in created if note.file_url]
            for note in created:
                db.delete(note)
            db.commit()
            for path in paths:
                if path.resolve().parent == (ROOT / "uploads/notes").resolve():
                    path.unlink(missing_ok=True)
            assert db.query(Note).count() == before_count
        print("Verification notes cleaned up; existing records preserved.")


if __name__ == "__main__":
    main()
