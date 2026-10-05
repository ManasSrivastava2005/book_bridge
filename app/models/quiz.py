from datetime import datetime
from sqlalchemy import Integer, String, Text, Boolean, ForeignKey, DateTime, JSON, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Quiz(Base):
    __tablename__='quizzes'
    __table_args__=(CheckConstraint("status IN ('draft','published')"),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    title: Mapped[str]=mapped_column(String(200))
    subject_id: Mapped[int|None]=mapped_column(ForeignKey('curriculum_nodes.id'))
    topic_id: Mapped[int|None]=mapped_column(ForeignKey('curriculum_nodes.id'))
    book_id: Mapped[int|None]=mapped_column(ForeignKey('books.id'))
    chapter: Mapped[str|None]=mapped_column(String(200))
    status: Mapped[str]=mapped_column(String(20),default='draft')
    active: Mapped[bool]=mapped_column(Boolean,default=False)
    source_kind: Mapped[str]=mapped_column(String(30),default='librarian_original')
    source_reference: Mapped[str|None]=mapped_column(String(1000))
    permission_confirmed: Mapped[bool]=mapped_column(Boolean,default=False)
    created_by: Mapped[int]=mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
    updated_at: Mapped[datetime]=mapped_column(DateTime,server_default=func.now(),onupdate=func.now())

class QuizQuestion(Base):
    __tablename__='quiz_questions'
    __table_args__=(UniqueConstraint('quiz_id','position'),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    quiz_id: Mapped[int]=mapped_column(ForeignKey('quizzes.id'),index=True)
    position: Mapped[int]=mapped_column(Integer)
    prompt: Mapped[str]=mapped_column(Text)
    options: Mapped[list]=mapped_column(JSON)
    correct_index: Mapped[int]=mapped_column(Integer)
    explanation: Mapped[str]=mapped_column(Text)
