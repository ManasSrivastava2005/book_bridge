from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class NoteBase(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    subject: Optional[str] = None
    semester: Optional[int] = None
    branch: Optional[str] = None
    file_url: Optional[str] = None
    file_type: Optional[str] = "PDF"
    file_size: Optional[str] = "1.2 MB"
    access_level: Optional[str] = "public"
    status: Optional[str] = "published"
    library_id: Optional[int] = 1

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    subject: Optional[str] = None
    semester: Optional[int] = None
    branch: Optional[str] = None
    file_url: Optional[str] = None
    access_level: Optional[str] = None
    status: Optional[str] = None

class NoteResponse(NoteBase):
    id: int
    user_id: int
    download_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
