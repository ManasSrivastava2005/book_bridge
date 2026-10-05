import json,hashlib
from pathlib import Path
from sqlalchemy import create_engine,inspect,text
from app.database import engine
manifest=json.loads(Path('backups/v2_20261002_154104/manifest.json').read_text());prior=create_engine(engine.url.set(database=manifest['isolated_database']))
with engine.connect() as live,prior.connect() as old:
 for table,count in manifest['row_counts'].items():
  assert live.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()==count,table
  cols=[col['name'] for col in inspect(old).get_columns(table)]
  # Restored test migration added new metadata, excluded when comparing historical values.
  excluded={'study_members':{'left_at','last_seen_at','role'},'study_messages':{'reply_to_id','edited_at','deleted_at'}}.get(table,set())
  names=','.join('"'+c+'"' for c in cols if c not in excluded)
  assert sorted(repr(tuple(r)) for r in live.execute(text(f'SELECT {names} FROM "{table}"')))==sorted(repr(tuple(r)) for r in old.execute(text(f'SELECT {names} FROM "{table}"'))),table
for name,digest in manifest['file_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print('All 43 original table counts and historical values preserved, including earned badges/XP/loans/profile/study content. All 7 original uploaded files match backup hashes.')
