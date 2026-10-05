from app.models.resource_usage import ResourceUsage
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import func, update
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
import uuid

from app.database import get_db
from app.dependencies import get_current_user
from app.models.note import Note
from app.models.user import User
from app.schemas.note import NoteCreate, NoteResponse

router = APIRouter(prefix="/notes", tags=["Notes"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "notes")
PRIVATE_UPLOAD_DIR = os.path.join(os.path.dirname(UPLOAD_DIR), "..", "private_uploads", "notes")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", response_model=List[NoteResponse])
def get_notes(
    subject: Optional[str] = None,
    semester: Optional[int] = None,
    branch: Optional[str] = None,
    search: Optional[str] = None,
    library_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    List published notes with filters for subject, semester, branch, search.
    """
    query = db.query(Note).filter(Note.status == "published")

    if subject and subject != "all":
        query = query.filter(Note.subject.ilike(f"%{subject}%"))
    if semester:
        query = query.filter(Note.semester == semester)
    if branch and branch != "all":
        query = query.filter(Note.branch.ilike(f"%{branch}%"))
    if library_id:
        query = query.filter(Note.library_id == library_id)
    if search:
        query = query.filter(
            Note.title.ilike(f"%{search}%")
            | Note.description.ilike(f"%{search}%")
            | Note.subject.ilike(f"%{search}%")
        )

    return query.order_by(Note.created_at.desc()).all()


@router.get("/my", response_model=List[NoteResponse])
def my_notes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Note).filter(Note.user_id == current_user.id, Note.status == "personal").order_by(Note.created_at.desc()).all()


@router.get("/personal-files/{filename}")
def personal_file(filename: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    note = db.query(Note).filter(Note.file_url == f"/notes/personal-files/{filename}", Note.status == "personal", Note.user_id == current_user.id).first()
    if not note or os.path.basename(filename) != filename or "\\" in filename:
        raise HTTPException(status_code=404, detail="Note not found")
    path = os.path.join(PRIVATE_UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path, filename=filename.split("_", 1)[-1], headers={"Cache-Control": "private, no-store"})


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id, Note.status == "published").first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".ppt", ".pptx"}
ALLOWED_MIMES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/octet-stream",
}


@router.post("/upload", response_model=NoteResponse, status_code=201)
async def upload_note_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    subject: str = Form(...),
    semester: int = Form(..., ge=1, le=8),
    branch: Optional[str] = Form("Computer Science & Engineering"),
    description: Optional[str] = Form(None),
    access_level: Optional[str] = Form("public"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _store_note(False, file, title, subject, semester, branch, description, access_level, db, current_user)


@router.post("/my/upload", response_model=NoteResponse, status_code=201)
async def upload_personal_note(
    file: UploadFile = File(...),
    title: str = Form(...),
    subject: str = Form(...),
    semester: int = Form(..., ge=1, le=8),
    branch: Optional[str] = Form("Computer Science & Engineering"),
    description: Optional[str] = Form(None),
    access_level: Optional[str] = Form("public"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _store_note(True, file, title, subject, semester, branch, description, access_level, db, current_user)


async def _store_note(
    personal: bool,
    file: UploadFile,
    title: str,
    subject: str,
    semester: int,
    branch: Optional[str],
    description: Optional[str],
    access_level: Optional[str],
    db: Session,
    current_user: User,
):
    """
    Upload an educational lecture note or study document.
    Enforces authorization, MIME & extension check, safe filename generation, and 25MB size limit.
    """
    # 1. Role-based authorization: Only librarians or admins can publish notes
    if not personal and current_user.role.value not in ("librarian", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Study material uploads are restricted to authorized library staff and educators.",
        )

    # Match database limits before saving a file or committing metadata.
    title = title.strip()
    subject = subject.strip()
    branch = (branch or "Computer Science & Engineering").strip()
    access_level = (access_level or "public").strip()
    for name, value, limit in (
        ("Title", title, 255), ("Subject", subject, 100),
        ("Branch", branch, 100), ("Access level", access_level, 50),
    ):
        if not value or len(value) > limit:
            raise HTTPException(status_code=422, detail=f"{name} must contain 1 to {limit} characters.")

    # 2. File presence & name check
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file selected for upload.",
        )

    # 3. Extension check
    _, ext = os.path.splitext(file.filename)
    ext_lower = ext.lower()
    if ext_lower not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed types: PDF, DOC, DOCX, PPT, PPTX, TXT.",
        )

    # 4. MIME type check
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{file.content_type}'.",
        )

    # 5. Read file contents and check size limit (25 MB)
    contents = await file.read(MAX_FILE_SIZE + 1)
    file_size_bytes = len(contents)
    if file_size_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds maximum allowed size of 25 MB.",
        )
    if file_size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    # 6. Format readable file size
    if file_size_bytes >= 1024 * 1024:
        size_str = f"{round(file_size_bytes / (1024 * 1024), 1)} MB"
    else:
        size_str = f"{round(file_size_bytes / 1024, 1)} KB"

    # 7. Generate secure unique filename (UUID + sanitized original name, preventing path traversal)
    original_stem = os.path.splitext(os.path.basename(file.filename.replace("\\", "/")))[0]
    clean_stem = "".join(c for c in original_stem if c.isalnum() or c in "_- ")[:64].strip() or "note"
    safe_filename = f"{uuid.uuid4().hex}_{clean_stem}{ext_lower}"
    storage_dir = PRIVATE_UPLOAD_DIR if personal else UPLOAD_DIR
    destination_path = os.path.join(storage_dir, safe_filename)

    # 8. Determine file type display label
    file_type_label = ext_lower.replace(".", "").upper()

    # 9. Store relative file URL accessible via StaticFiles
    file_url = f"/notes/personal-files/{safe_filename}" if personal else f"/uploads/notes/{safe_filename}"

    # 10. Persist metadata into PostgreSQL
    note = Note(
        user_id=current_user.id,
        library_id=current_user.library_id,
        title=title.strip(),
        description=description.strip() if description else None,
        subject=subject.strip(),
        semester=semester,
        branch=branch.strip() if branch else "Computer Science & Engineering",
        file_url=file_url,
        file_type=file_type_label,
        file_size=size_str,
        access_level="private" if personal else access_level or "public",
        status="personal" if personal else "published",
        download_count=0,
    )
    file_created = False
    try:
        os.makedirs(storage_dir, exist_ok=True)
        with open(destination_path, "xb") as destination:
            file_created = True
            destination.write(contents)
        db.add(note)
        db.flush()
        db.refresh(note)
        # Validate before commit so a response error cannot leave a published row.
        response = NoteResponse.model_validate(note)
        db.commit()
    except (OSError, SQLAlchemyError, ValidationError) as exc:
        db.rollback()
        if file_created:
            try:
                os.remove(destination_path)
            except OSError:
                logger.error("Could not remove an uncommitted note upload")
        logger.error("Note upload failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Unable to save the note. Please try again.") from exc
    return response


@router.post("/", response_model=NoteResponse, status_code=201)
def create_note(
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a note entry (with pre-existing file URL)."""
    if current_user.role.value not in ("librarian", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Study material uploads are restricted to authorized library staff and educators.",
        )
    if note_data.status == "personal":
        raise HTTPException(status_code=422, detail="Use the personal upload endpoint for private notes.")
    new_note = Note(
        **note_data.model_dump(exclude={"library_id"}),
        user_id=current_user.id,
        library_id=current_user.library_id,
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note


@router.post("/{note_id}/download")
def record_download(note_id: int, db: Session = Depends(get_db)):
    """Increment download count when a note is downloaded."""
    result = db.execute(
        update(Note)
        .where(Note.id == note_id, Note.status == "published")
        .values(download_count=func.coalesce(Note.download_count, 0) + 1)
        .returning(Note.download_count, Note.file_url, Note.title)
    ).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Note not found")
    db.add(ResourceUsage(resource_kind='note',resource_id=note_id,title=result.title))
    db.commit()
    return {"status": "ok", "download_count": result.download_count, "file_url": result.file_url}


@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.status == "personal" and note.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Note not found")

    # Only uploader or librarian/admin can delete
    if note.user_id != current_user.id and current_user.role.value not in ("librarian", "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this note")

    private_filename = os.path.basename(note.file_url or "") if note.status == "personal" else None
    db.delete(note)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This note is referenced by a curriculum or contribution history and cannot be deleted.") from exc
    if private_filename and "\\" not in private_filename:
        try:
            os.remove(os.path.join(PRIVATE_UPLOAD_DIR, private_filename))
        except FileNotFoundError:
            pass
        except OSError:
            logger.error("Could not remove a deleted personal note file")
    return None
