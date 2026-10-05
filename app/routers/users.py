import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.put("/me", response_model=UserResponse)
def update_me(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    if user_data.name is not None and user_data.name.strip():
        current_user.name = user_data.name.strip()
    if user_data.email is not None:
        current_user.email = user_data.email
    if user_data.student_id is not None:
        current_user.student_id = user_data.student_id.strip()
    if user_data.branch is not None:
        current_user.branch = user_data.branch.strip()
    if user_data.semester is not None:
        current_user.semester = user_data.semester
    if user_data.profile_image is not None:
        current_user.profile_image = user_data.profile_image
    if 'library_id' in user_data.model_fields_set and user_data.library_id != current_user.library_id:
        raise HTTPException(403, 'Library membership is managed by library staff')

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/profile-picture", response_model=UserResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload and set student/librarian profile avatar image.
    Validates MIME type, file extension, and size.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Please upload JPG, PNG, or WebP."
        )

    # Read file content & check size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds maximum allowed limit (5MB)."
        )

    # Generate unique safe filename
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    # Relative public URL
    image_url = f"/uploads/avatars/{filename}"
    current_user.profile_image = image_url
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/profile-picture", response_model=UserResponse)
def remove_profile_picture(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove profile avatar and reset to default initials.
    """
    if current_user.profile_image and current_user.profile_image.startswith("/uploads/avatars/"):
        filename = os.path.basename(current_user.profile_image)
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

    current_user.profile_image = None
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user
