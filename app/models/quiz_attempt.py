from datetime import datetime
from sqlalchemy import Integer,String,DateTime,JSON,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class QuizAttempt(Base):
    __tablename__='quiz_attempts'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    quiz_id:Mapped[int]=mapped_column(ForeignKey('quizzes.id'))
    title:Mapped[str]=mapped_column(String(200))
    book_id:Mapped[int|None]=mapped_column(Integer)
    subject_id:Mapped[int|None]=mapped_column(Integer)
    topic_id:Mapped[int|None]=mapped_column(Integer)
    chapter:Mapped[str|None]=mapped_column(String(200))
    questions:Mapped[list]=mapped_column(JSON)
    answers:Mapped[list|None]=mapped_column(JSON)
    score:Mapped[int|None]=mapped_column(Integer)
    started_at:Mapped[datetime]=mapped_column(DateTime)
    submitted_at:Mapped[datetime|None]=mapped_column(DateTime)
