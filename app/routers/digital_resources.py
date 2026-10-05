from app.models.resource_usage import ResourceUsage
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import io
import logging
from pathlib import Path
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from pypdf import PdfReader
from app.services import ebook_storage

from app.database import get_db
from app.dependencies import require_role, get_current_user, bearer_scheme
from fastapi.security import HTTPAuthorizationCredentials
from app.models.digital_resource import DigitalResource
from app.models.user import User
from app.models.library import Library
from app.schemas.digital_resource import DigitalResourceCreate, DigitalResourceResponse

router = APIRouter(prefix="/digital-resources", tags=["Digital Resources"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "ebooks")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", response_model=List[DigitalResourceResponse])
def get_digital_resources(
    resource_type: Optional[str] = None,
    subject: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    library_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    List digital resources with filters for open access, campus PDFs, subjects, and search queries.
    """
    query = db.query(DigitalResource).filter(DigitalResource.is_published == True, DigitalResource.archived_at.is_(None), DigitalResource.reviewed_by.isnot(None))

    if resource_type and resource_type != "all":
        query = query.filter(DigitalResource.resource_type == resource_type)
    if subject:
        query = query.filter(DigitalResource.subject.ilike(f"%{subject}%"))
    if category:
        query = query.filter(DigitalResource.category.ilike(f"%{category}%"))
    if library_id:
        query = query.filter(DigitalResource.library_id == library_id)
    if search:
        query = query.filter(
            DigitalResource.title.ilike(f"%{search}%")
            | DigitalResource.author.ilike(f"%{search}%")
            | DigitalResource.description.ilike(f"%{search}%")
        )

    return query.order_by(DigitalResource.created_at.desc()).all()


MAX_PDF_BYTES = 25 * 1024 * 1024
COVER_DIR = Path(__file__).resolve().parents[2] / 'uploads' / 'covers'


@router.post('/covers', status_code=201)
async def upload_cover(file: UploadFile = File(...), user: User = Depends(require_role('librarian','admin'))):
    """Re-encode bounded raster covers; original filenames/metadata are discarded."""
    contents=await file.read(3*1024*1024+1)
    if not contents or len(contents)>3*1024*1024:
        raise HTTPException(400,'Choose a cover image up to 3 MB.')
    def convert():
        from PIL import Image
        try:
            with Image.open(io.BytesIO(contents)) as source:
                if source.format not in ('PNG','JPEG','WEBP') or source.width*source.height>16000000:
                    raise ValueError('Unsupported image')
                source.thumbnail((1200,1600))
                output=io.BytesIO();source.convert('RGB').save(output,format='JPEG',quality=85)
                return output.getvalue()
        except Exception:
            raise HTTPException(400,'Choose a readable PNG, JPEG or WebP cover under 16 megapixels.') from None
    converted=await run_in_threadpool(convert)
    name=uuid.uuid4().hex+'.jpg'
    try:
        COVER_DIR.mkdir(parents=True,exist_ok=True)
        with (COVER_DIR/name).open('xb') as stream:stream.write(converted)
    except OSError:
        raise HTTPException(500,'Could not save the cover image.') from None
    return {'cover_image':'/uploads/covers/'+name}


def validate_pdf(contents):
    try:
        document = PdfReader(io.BytesIO(contents))
        if document.is_encrypted or not len(document.pages):
            raise ValueError('Encrypted or empty PDF')
    except Exception:
        raise HTTPException(400, 'Choose a readable, unencrypted PDF with at least one page.') from None


@router.post('/upload', response_model=DigitalResourceResponse, status_code=201)
async def upload_pdf(file: UploadFile = File(...), metadata: str = Form(...),
                     db: Session = Depends(get_db), user: User = Depends(require_role('librarian', 'admin'))):
    try:
        payload = DigitalResourceCreate.model_validate_json(metadata)
    except ValidationError:
        raise HTTPException(422, 'Check the resource metadata and required title/author fields.') from None
    ebook_storage.validate_managed_metadata(payload)
    if payload.library_id is not None and not db.get(Library, payload.library_id):
        raise HTTPException(404, 'Library not found')
    if not file.filename or not file.filename.lower().endswith('.pdf') or file.content_type not in ('application/pdf', 'application/octet-stream'):
        raise HTTPException(400, 'Only PDF documents are supported.')
    contents = await file.read(MAX_PDF_BYTES + 1)
    if not contents or len(contents) > MAX_PDF_BYTES:
        raise HTTPException(400, 'Choose a non-empty PDF no larger than 25 MB.')
    if not contents.startswith(b'%PDF-'):
        raise HTTPException(400, 'The uploaded document is not a PDF.')
    await run_in_threadpool(validate_pdf, contents)
    filename = uuid.uuid4().hex + '.pdf'
    path = ebook_storage.PRIVATE_EBOOK_DIR / filename
    values = payload.model_dump()
    values.update(file_url='/digital-resources/files/' + filename, external_url=None, resource_type='uploaded_pdf')
    resource = DigitalResource(**values, uploaded_by=user.id)
    if resource.is_published:ebook_storage.record_review(resource,user)
    created = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            created = True
            stream.write(contents)
        db.add(resource)
        db.flush()
        db.refresh(resource)
        response = DigitalResourceResponse.model_validate(resource)
        db.commit()
        return response
    except (OSError, SQLAlchemyError, ValidationError):
        db.rollback()
        if created:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).error('Could not clean up failed PDF upload')
        raise HTTPException(500, 'Unable to save this PDF. Please try again.') from None


@router.get('/files/{filename}')
def read_pdf(filename: str, download: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    url = '/digital-resources/files/' + filename
    if not ebook_storage.managed(url):
        raise HTTPException(404, 'PDF not found')
    resource = db.query(DigitalResource).filter(DigitalResource.file_url == url).first()
    if not resource:
        raise HTTPException(404, 'PDF not found')
    ebook_storage.authorize(resource, user)
    if download and not resource.download_allowed:
        raise HTTPException(403, 'Downloads are disabled for this resource.')
    path = ebook_storage.PRIVATE_EBOOK_DIR / filename
    if not path.is_file():
        raise HTTPException(404, 'PDF file not found')
    if download:
        db.add(ResourceUsage(resource_kind='digital_resource',resource_id=resource.id,title=resource.title,user_id=user.id))
        db.commit()
    return FileResponse(path, media_type='application/pdf', filename='book.pdf',
                        content_disposition_type='attachment' if download else 'inline',
                        headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.get("/{resource_id}", response_model=DigitalResourceResponse)
def get_digital_resource(resource_id: int, db: Session = Depends(get_db), credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Get details for a single digital e-book or resource."""
    resource = db.query(DigitalResource).filter(DigitalResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Digital resource not found")
    if not resource.is_published or resource.archived_at is not None or not resource.reviewed_by:
        if credentials is None:
            raise HTTPException(404, 'Digital resource not found')
        user = get_current_user(credentials, db)
        if user.role.value not in ('librarian', 'admin'):
            raise HTTPException(404, 'Digital resource not found')
    return resource


@router.post("/", response_model=DigitalResourceResponse, status_code=201)
def create_digital_resource(
    resource_data: DigitalResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("librarian", "admin")),
):
    """Register or publish an authorized digital e-book (librarian/admin only)."""
    if resource_data.library_id is not None and not db.get(Library, resource_data.library_id):
        raise HTTPException(404, 'Library not found')
    if ebook_storage.managed(resource_data.file_url):
        raise HTTPException(422, 'Use PDF upload to create a managed resource.')
    new_res = DigitalResource(
        **resource_data.model_dump(),
        uploaded_by=current_user.id,
    )
    if new_res.is_published:ebook_storage.record_review(new_res,current_user)
    db.add(new_res)
    db.commit()
    db.refresh(new_res)
    return new_res


@router.delete("/{resource_id}", status_code=204)
def delete_digital_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("librarian", "admin")),
):
    """Delete digital resource (librarian/admin only)."""
    resource = db.query(DigitalResource).filter(DigitalResource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Digital resource not found")
    if (resource.file_url or '').startswith('/uploads/'):
        raise HTTPException(409,'Archive legacy resources to preserve file access controls and history.')
    path = ebook_storage.PRIVATE_EBOOK_DIR / resource.file_url.rsplit('/', 1)[-1] if ebook_storage.managed(resource.file_url) else None
    db.delete(resource)
    from sqlalchemy.exc import IntegrityError
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This resource is referenced by a curriculum or reading history and cannot be deleted.") from exc
    if path:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logging.getLogger(__name__).error('Could not remove deleted managed PDF')
    return None
