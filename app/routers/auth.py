from app.services.academic import save_profile
from app.services.badges import award_badges
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse, UserUpdate
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ──────────────────────────────────────────────
# REGISTER — POST /auth/register
# ──────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        student_id=user_data.student_id,
        branch=user_data.branch,
        semester=user_data.semester,
        library_id=None,
    )
    db.add(new_user)
    db.flush()
    if user_data.academic is not None:
        save_profile(db, new_user, user_data.academic)
    db.commit()
    db.refresh(new_user)
    return new_user


# ──────────────────────────────────────────────
# LOGIN — POST /auth/login
# ──────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if login_data.portal == "staff" and user.role.value not in ("librarian", "admin"):
        raise HTTPException(403, "Use Student sign in for this account")
    if login_data.portal == "student" and user.role.value != "student":
        raise HTTPException(403, "Use Staff sign in for this account")

    from app.services.xp import award_login
    award_login(db, user)
    from app.services.badges import award_badges
    award_badges(db, user.id)
    db.commit()
    access_token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=access_token)


# ──────────────────────────────────────────────
# GET CURRENT USER — GET /auth/me
# ──────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ──────────────────────────────────────────────
# UPDATE PROFILE — PUT /auth/profile
# ──────────────────────────────────────────────
@router.put("/profile", response_model=UserResponse)
def update_profile(
    profile_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """
    Update authenticated student or librarian profile details with database persistence.
    """
    if profile_data.name is not None and profile_data.name.strip():
        current_user.name = profile_data.name.strip()
    if profile_data.student_id is not None:
        current_user.student_id = profile_data.student_id.strip()
    if profile_data.branch is not None:
        current_user.branch = profile_data.branch.strip()
    if profile_data.semester is not None:
        current_user.semester = profile_data.semester
    if profile_data.profile_image is not None:
        current_user.profile_image = profile_data.profile_image
    if 'library_id' in profile_data.model_fields_set and profile_data.library_id != current_user.library_id:
        raise HTTPException(403, 'Library membership is managed by library staff')

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user
