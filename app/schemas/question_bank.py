from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class QuestionBankBase(BaseModel):
    title: str
    description: Optional[str] = None
    subject: str
    semester: int
    branch: str
    exam_type: str = "End-Term"
    academic_year: str = "2025-2026"
    file_url: Optional[str] = None
    file_type: str = "PDF"
    total_questions: int = 25
    library_id: Optional[int] = 1

class QuestionBankCreate(QuestionBankBase):
    pass

class QuestionBankResponse(QuestionBankBase):
    id: int
    user_id: Optional[int] = None
    download_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
