from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID,uuid4
import hashlib,json,logging
from fastapi import APIRouter,Depends,File,Form,UploadFile,HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.models.syllabus_upload import SyllabusUpload
from app.schemas.personal_curriculum import PersonalCurriculumWrite
from app.services.syllabus_processing import process_pdf,MAX_BYTES
from app.services.personal_curriculum import save_personal
from app.routers.curriculum_workspace import SubjectWrite

router=APIRouter(prefix='/academic/syllabi',tags=['Private syllabus'])
PRIVATE_SYLLABUS_DIR=Path(__file__).resolve().parents[2]/'private_uploads'/'syllabi'

def owned(db,id,user,lock=False):
    query=db.query(SyllabusUpload).filter_by(id=id,user_id=user.id).filter(SyllabusUpload.state!='deleted')
    row=(query.with_for_update() if lock else query).first()
    if not row:raise HTTPException(404,'Syllabus not found')
    return row

def output(row):
    return {'id':row.id,'original_name':row.original_name,'state':row.state,'created_at':row.created_at,'confirmed_at':row.confirmed_at,'curriculum_id':row.curriculum_id,'subject_id':row.subject_id,'extracted_text':row.extracted_text,'proposal':row.proposal}

@router.get('')
def listing(db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    return [{'id':r.id,'original_name':r.original_name,'state':r.state,'subject_id':r.subject_id,'created_at':r.created_at} for r in db.query(SyllabusUpload).filter_by(user_id=user.id).filter(SyllabusUpload.state!='deleted').order_by(SyllabusUpload.created_at.desc())]

@router.post('',status_code=201)
async def upload(file:UploadFile=File(...),request_id:UUID=Form(...),subject_id:int|None=Form(None),db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    if not file.filename or not file.filename.lower().endswith('.pdf') or file.content_type not in ('application/pdf','application/octet-stream'):raise HTTPException(400,'Choose a PDF syllabus.')
    contents=await file.read(MAX_BYTES+1);digest=hashlib.sha256(contents).hexdigest()
    # Same lock order as confirmation and curriculum editing.
    db.query(User).filter_by(id=user.id).with_for_update().one()
    from app.services.curriculum_workspace import owned_subject
    subject=owned_subject(db,user,subject_id) if subject_id is not None else None
    previous=db.query(SyllabusUpload).filter_by(user_id=user.id,request_key=str(request_id)).first()
    if previous:
        if previous.state=='deleted':raise HTTPException(410,'This upload was deleted. Select the PDF again to create a new upload.')
        if previous.content_hash!=digest or previous.subject_id!=subject_id:raise HTTPException(409,'Upload request already used for a different PDF or subject.')
        return output(previous)
    text,proposal=await run_in_threadpool(process_pdf,contents,subject.title if subject else None)
    filename=uuid4().hex+'.pdf';path=PRIVATE_SYLLABUS_DIR/filename
    row=SyllabusUpload(user_id=user.id,subject_id=subject_id,request_key=str(request_id),content_hash=digest,filename=filename,original_name=Path(file.filename.replace('\\','/')).name[:255],extracted_text=text,proposal=proposal)
    created=False
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:created=True;stream.write(contents)
        db.add(row);db.commit();db.refresh(row)
    except (OSError,SQLAlchemyError):
        db.rollback()
        if created:path.unlink(missing_ok=True)
        raise HTTPException(500,'Could not save the private syllabus.') from None
    return output(row)

def mark_deleted(row):
    # Keep the minimal record for idempotency/history, never its extracted private content.
    row.state='deleted';row.extracted_text='';row.proposal={};row.confirmation_hash=None

def purge_files(rows):
    # Access is revoked by the committed tombstone even if filesystem cleanup fails.
    for row in rows:
        try:(PRIVATE_SYLLABUS_DIR/row.filename).unlink(missing_ok=True)
        except OSError:logging.getLogger(__name__).warning('Private syllabus %s deleted; file cleanup needs retry.',row.id)

@router.delete('/{id}',status_code=204)
def delete_upload(id:int,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    row=db.query(SyllabusUpload).filter_by(id=id,user_id=user.id).with_for_update().first()
    if not row:raise HTTPException(404,'Syllabus not found')
    mark_deleted(row);db.commit();purge_files([row])

@router.get('/{id}')
def read(id:int,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):return output(owned(db,id,user))

@router.get('/{id}/file')
def file(id:int,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    row=owned(db,id,user);path=PRIVATE_SYLLABUS_DIR/row.filename
    if not path.is_file():raise HTTPException(404,'Syllabus file not found')
    return FileResponse(path,media_type='application/pdf',filename='syllabus.pdf',headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

@router.post('/{id}/confirm')
def confirm(id:int,payload:PersonalCurriculumWrite,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    row=owned(db,id,user,True)
    if row.subject_id is not None:raise HTTPException(409,'Confirm this syllabus inside its subject to preserve other subjects.')
    digest=hashlib.sha256(json.dumps(payload.model_dump(),sort_keys=True).encode()).hexdigest()
    if row.state=='confirmed':
        if row.confirmation_hash!=digest:raise HTTPException(409,'This syllabus was already confirmed. Edit your personal curriculum for subsequent changes.')
        return output(row)
    curriculum=save_personal(db,user,payload)
    row.curriculum_id=curriculum.id;row.state='confirmed';row.confirmation_hash=digest;row.confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit();return output(row)

@router.post('/{id}/confirm-subject/{subject_id}')
def confirm_subject(id:int,subject_id:int,payload:SubjectWrite,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    from app.services.curriculum_workspace import owned_subject,update_subject
    db.query(User).filter_by(id=user.id).with_for_update().one()
    subject=owned_subject(db,user,subject_id)
    row=owned(db,id,user,True)
    if row.subject_id not in (None,subject_id):raise HTTPException(409,'This PDF belongs to another subject.')
    digest=hashlib.sha256(json.dumps({'subject_id':subject_id,**payload.model_dump()},sort_keys=True).encode()).hexdigest()
    if row.state=='confirmed':
        if row.confirmation_hash!=digest:raise HTTPException(409,'This PDF was already confirmed. Edit the saved curriculum instead.')
        return output(row)
    if not payload.subject.children or not any(u.children for u in payload.subject.children):
        raise HTTPException(422,'Review and add at least one unit with a topic before confirming.')
    update_subject(db,user,subject_id,payload)
    row.subject_id=subject_id;row.curriculum_id=subject.curriculum_id
    row.state='confirmed';row.confirmation_hash=digest;row.confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit();return output(row)
