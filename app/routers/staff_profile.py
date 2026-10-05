"""Staff self-profile, sharing the existing account and avatar storage."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User

router = APIRouter(prefix='/admin/profile', tags=['Staff profile'])

class StaffProfileWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)

def profile_data(user):
    return {'name': user.name, 'email': user.email, 'role': user.role.value,
            'profile_image': user.profile_image,
            'library': {'id': user.library.id, 'name': user.library.name} if user.library else None}

@router.get('')
def profile(user: User = Depends(require_role('librarian', 'admin'))):
    return profile_data(user)

@router.patch('')
def update(payload: StaffProfileWrite, db: Session = Depends(get_db),
           user: User = Depends(require_role('librarian', 'admin'))):
    user.name = payload.name
    db.commit()
    db.refresh(user)
    return profile_data(user)
