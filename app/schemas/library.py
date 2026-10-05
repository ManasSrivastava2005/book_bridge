from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class LibraryBase(BaseModel):
    name: str
    code: str
    campus: str
    address: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True

class LibraryCreate(LibraryBase):
    pass

class LibraryResponse(LibraryBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
