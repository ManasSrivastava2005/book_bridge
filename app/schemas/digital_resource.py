from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlsplit, unquote
from typing import Optional, Literal
from app.services.ebook_storage import managed

class DigitalResourceBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    isbn: Optional[str] = Field(default=None, max_length=50)
    resource_type: str = Field(default="open_access", max_length=50)
    access_type: str = Field(default="free", max_length=50)
    provider: str = Field(default="Project Gutenberg", min_length=1, max_length=100)
    library_id: Optional[int] = 1
    file_url: Optional[str] = Field(default=None, max_length=500)
    external_url: Optional[str] = Field(default=None, max_length=500)
    cover_image: Optional[str] = Field(default=None, max_length=500)
    subject: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = Field(default=None, max_length=100)
    language: str = Field(default="English", max_length=50)
    publication_year: Optional[int] = None
    license_name: str = Field(default="Public Domain / Open Access", max_length=100)
    license_url: Optional[str] = Field(default=None, max_length=500)
    distribution_basis: Optional[Literal["public_domain","open_license","permission"]] = None
    rights_evidence: Optional[str] = Field(default=None, max_length=4000)
    is_published: bool = True
    download_allowed: bool = True

class DigitalResourceCreate(DigitalResourceBase):
    @field_validator('title', 'author')
    @classmethod
    def readable_name(cls, value):
        if not value.strip():
            raise ValueError('Title and author cannot be blank')
        return value.strip()

    @field_validator('file_url', 'external_url', 'cover_image', 'license_url')
    @classmethod
    def safe_link(cls, value):
        if not value:
            return None
        value = value.strip()
        if any(ord(char) < 32 for char in value) or '\\' in value:
            raise ValueError('Provide a valid HTTP(S) URL or existing /uploads/ path')
        if managed(value):
            return value
        parsed = urlsplit(value)
        if value.startswith('/uploads/') and '..' not in unquote(parsed.path).split('/'):
            return value
        if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password:
            return value
        raise ValueError('Provide a valid HTTP(S) URL or existing /uploads/ path')

class DigitalResourceResponse(DigitalResourceBase):
    archived_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    id: int
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
