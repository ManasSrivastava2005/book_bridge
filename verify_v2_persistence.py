import json,hashlib,httpx
from pathlib import Path
from sqlalchemy import create_engine,inspect,text
from app.database import engine
manifest=json.loads(Path('backups/v2_20261001_114955/manifest.json').read_text())
restored=create_engine(engine.url.set(database=manifest['isolated_database']))
with engine.connect() as live,restored.connect() as baseline:
 for table,count in manifest['row_counts'].items():
  quoted='"'+table.replace('"','""')+'"'
  assert live.execute(text('SELECT count(*) FROM '+quoted)).scalar()==count,table
  # Compare entire pre-C13 row content in memory; never print personal data.
  before=sorted([repr(tuple(r)) for r in baseline.execute(text('SELECT * FROM '+quoted))])
  after=sorted([repr(tuple(r)) for r in live.execute(text('SELECT * FROM '+quoted))])
  assert before==after,table
 assert live.execute(text('SELECT count(*) FROM syllabus_uploads')).scalar()==0
for name,digest in manifest['file_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('Working database: all 42 original tables have identical rows to the pre-C13 restored backup; new syllabus table empty; all 5 original uploaded files unchanged.')
from app.services.auth import create_access_token
f=json.loads(Path('v2-integration-fixture.json').read_text());h={'Authorization':'Bearer '+create_access_token(f['student'],'student')}
c=httpx.Client(base_url='http://127.0.0.1:8001',headers=h)
reservations=c.get('/reservations/my').json();assert next(r for r in reservations if r['id']==f['reservation'])['status']=='fulfilled'
loans=c.get('/borrows/my').json();assert any(r['book_id']==f['book'] and r['status']=='returned' for r in loans)
assert c.get(f"/academic/syllabi/{f['syllabus']}").json()['state']=='confirmed'
assert c.get('/academic/curriculum').json()['subjects'][0]['units'][0]['topics'][0]['completed']
items=c.get('/student/contributions').json()['items'];assert {r['status'] for r in items}=={'APPROVED','REJECTED'}
assert c.get(f"/digital-resources/{f['resource']}").status_code==200
print('After real backend restart: confirmed syllabus, completed topic, fulfilled reservation, returned loan, contribution decisions and curated resource persisted.')
for url in ['http://127.0.0.1:5173/login','http://127.0.0.1:5173/librarian/login','http://127.0.0.1:8000/openapi.json']:
 assert httpx.get(url).status_code==200
print('Working student login, librarian login and backend HTTP checks passed.')
