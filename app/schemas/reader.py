from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

PageNumber = Annotated[int, Field(strict=True, ge=1, le=100000)]

class ReaderBookmark(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page: PageNumber
    note: str = Field(default='', max_length=2000)

class HighlightRect(BaseModel):
    model_config = ConfigDict(extra='forbid')
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    width: float = Field(gt=0, le=1, allow_inf_nan=False)
    height: float = Field(gt=0, le=1, allow_inf_nan=False)

    @model_validator(mode='after')
    def within_page(self):
        if self.x+self.width > 1.001 or self.y+self.height > 1.001:
            raise ValueError('Highlight must remain inside the page')
        return self

class ReaderHighlight(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=64, pattern=r'^[a-zA-Z0-9-]+$')
    page: PageNumber
    text: str = Field(min_length=1, max_length=4000)
    note: str = Field(default='', max_length=2000)
    rects: list[HighlightRect] = Field(min_length=1, max_length=100)

class ReaderData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    page: PageNumber = 1
    total_pages: PageNumber | None = None
    document_key: str = Field(default='', max_length=128)
    bookmarks: list[ReaderBookmark] = Field(default_factory=list, max_length=200)
    highlights: list[ReaderHighlight] = Field(default_factory=list, max_length=200)
    theme: Literal['light', 'sepia', 'dark'] = 'light'

    @model_validator(mode='after')
    def check_pages(self):
        pages = [self.page] + [b.page for b in self.bookmarks] + [h.page for h in self.highlights]
        if self.total_pages and max(pages) > self.total_pages:
            raise ValueError('Page number exceeds document page count')
        if len({b.page for b in self.bookmarks}) != len(self.bookmarks):
            raise ValueError('Duplicate bookmark page')
        if len({h.id for h in self.highlights}) != len(self.highlights):
            raise ValueError('Duplicate highlight ID')
        return self

class ReaderWrite(ReaderData):
    version: int = Field(ge=0, strict=True)

class ReaderResponse(ReaderData):
    version: int = 0
