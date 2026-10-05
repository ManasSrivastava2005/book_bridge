"""Local acceptance server: isolated restored DB and isolated upload directories."""
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.database as database

manifest=json.loads(Path('backups/v2_20260930_150236/manifest.json').read_text(encoding='utf-8'))
name=manifest['isolated_database']
assert name.startswith('bookbridge_v2_restore_') and name!=database.engine.url.database
database.engine=create_engine(database.engine.url.set(database=name))
database.SessionLocal=sessionmaker(bind=database.engine)
from app.services import ebook_storage, contributions
root=Path('backups/v2_20260930_150236/acceptance-files').resolve()
root.mkdir(exist_ok=True)
ebook_storage.PRIVATE_EBOOK_DIR=root/'ebooks'
contributions.PRIVATE_DIR=root/'contributions-private'
contributions.PUBLIC_DIR=root/'contributions-public'
from app.main import app
from app.routers import digital_resources, syllabus, notes
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
notes.PRIVATE_UPLOAD_DIR=str(root/"notes-private")
contributions.PUBLIC_DIR.mkdir(exist_ok=True)
app.router.routes.insert(0,Mount("/uploads/contributions",app=StaticFiles(directory=str(contributions.PUBLIC_DIR))))
syllabus.PRIVATE_SYLLABUS_DIR=root/"syllabi"
digital_resources.COVER_DIR=root/"covers"

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8001)
