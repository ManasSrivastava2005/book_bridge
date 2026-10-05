from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    is_private: bool = Field(default=False, strict=True)
    title: str = Field(min_length=1, max_length=120)
    subject: str = Field(default='', max_length=100)
    description: str = Field(default='', max_length=2000)


class RoomArchive(BaseModel):
    model_config = ConfigDict(extra='forbid')
    archived: bool = Field(strict=True)


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    body: str = Field(min_length=1, max_length=4000)
    client_id: UUID
    reply_to_id: int | None = Field(None,gt=0)


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reason: str = Field(min_length=1, max_length=1000)


class RoomEdit(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=1,max_length=120)
    subject: str = Field(default='',max_length=100)
    description: str = Field(default='',max_length=2000)

class MessageEdit(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    body: str = Field(min_length=1,max_length=4000)
