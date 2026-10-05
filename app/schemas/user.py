from app.schemas.academic import AcademicWrite
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

class UserCreate(BaseModel):
    academic: Optional[AcademicWrite] = None
    name: str
    email: EmailStr
    password: str
    student_id: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    portal: Optional[Literal["student", "staff"]] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    student_id: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    profile_image: Optional[str] = None
    library_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    student_id: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    profile_image: Optional[str] = None
    library_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
