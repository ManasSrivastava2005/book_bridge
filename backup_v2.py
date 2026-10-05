"""Explicit local backup and isolated restore drill; never resets working data."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile
from sqlalchemy import create_engine, inspect, text
from app.database import engine

def run():
    root=Path(__file__).resolve().parent
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    target=root/'backups'/('v2_'+stamp)
    target.mkdir(parents=True,exist_ok=False)
    url=engine.url
    env=os.environ.copy()
    env.update(PGHOST=url.host or 'localhost',PGPORT=str(url.port or 5432),PGUSER=url.username or '',PGPASSWORD=url.password or '')
    binaries=Path(r'C:\Program Files\PostgreSQL\18\bin')
    def command(args):
        result=subprocess.run(args,env=env,capture_output=True)
        if result.returncode:raise RuntimeError('Database backup/restore command failed; no working data was changed.')
    def counts(connection):
        return {name:connection.execute(text('SELECT count(*) FROM "'+name.replace('"','""')+'"')).scalar() for name in inspect(connection).get_table_names()}
    with engine.connect() as c: before=counts(c)
    command([str(binaries/'pg_dump.exe'),'-Fc','--no-owner','--no-acl','-f',str(target/'database.dump'),url.database])
    command([str(binaries/'pg_restore.exe'),'--list',str(target/'database.dump')])
    files={}
    with zipfile.ZipFile(target/'uploaded-files.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for folder in ('uploads','private_uploads'):
            for path in (root/folder).rglob('*'):
                if path.is_file():
                    name=path.relative_to(root).as_posix()
                    archive.write(path,name)
                    files[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(target/'uploaded-files.zip') as archive:
        assert archive.testzip() is None
        assert all(hashlib.sha256(archive.read(n)).hexdigest()==h for n,h in files.items())
    database='bookbridge_v2_restore_'+stamp
    assert database!=url.database and database.startswith('bookbridge_v2_restore_')
    maintenance=create_engine(url.set(database='postgres'),isolation_level='AUTOCOMMIT')
    with maintenance.connect() as c:c.execute(text('CREATE DATABASE "'+database+'"'))
    command([str(binaries/'pg_restore.exe'),'--no-owner','--no-acl','--exit-on-error','-d',database,str(target/'database.dump')])
    restored=create_engine(url.set(database=database))
    with restored.connect() as c: after=counts(c)
    with engine.connect() as c: current=counts(c)
    if before!=after or before!=current:raise RuntimeError('Row counts changed during backup; compare before using the backup.')
    manifest={'created_at':stamp,'working_database':url.database,'isolated_database':database,'row_counts':after,'file_sha256':files,'restore_verified':True}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Verified backup:',target)
    print('Isolated restored database:',database)
    print('Tables:',len(after),'Uploaded files:',len(files))
    restored.dispose();maintenance.dispose()

if __name__=='__main__':run()
