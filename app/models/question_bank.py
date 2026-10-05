from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class QuestionBank(Base):
    """
    Exam preparation question bank: previous years questions, midterm/endterm papers, practice problem sets.
    """
    __tablename__ = "question_banks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    branch: Mapped[str] = mapped_column(String(100), nullable=False)

    # exam_type: "Mid-Term", "End-Term", "Quiz & Tests", "Practice Set"
    exam_type: Mapped[str] = mapped_column(String(50), default="End-Term")
    academic_year: Mapped[str] = mapped_column(String(20), default="2025-2026")

    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_type: Mapped[str] = mapped_column(String(20), default="PDF")
    total_questions: Mapped[int] = mapped_column(Integer, default=25)

    library_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("libraries.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    library = relationship("Library")
    uploader = relationship("User")
