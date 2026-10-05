"""Compare every original column and row around the additive migration."""
import json,sys,hashlib
from pathlib import Path
from sqlalchemy import create_engine,inspect,text
from app.database import engine
from migrate_curriculum_workspace import migrate

manifest=json.loads(Path('backups/v2_20261004_151927/manifest.json').read_text())
working='--working' in sys.argv
target=engine if working else create_engine(engine.url.set(database=manifest['isolated_database']))
def snapshot(connection,columns):
 return {table:sorted(repr(tuple(row)) for row in connection.execute(text('SELECT '+','.join('"'+c+'"' for c in cols)+' FROM "'+table+'"'))) for table,cols in columns.items()}
with target.begin() as connection:
 columns={t:[c['name'] for c in inspect(connection).get_columns(t)] for t in inspect(connection).get_table_names()}
 before=snapshot(connection,columns)
 migrate(connection);migrate(connection)
 assert before==snapshot(connection,columns),'Historical values changed'
for name,digest in manifest['file_sha256'].items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
print(('Working' if working else 'Isolated')+' migration applied twice: all original columns/rows and uploaded files preserved.')
