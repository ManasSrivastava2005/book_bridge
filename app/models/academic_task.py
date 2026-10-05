from datetime import datetime,date
from sqlalchemy import Integer,String,Date,DateTime,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class AcademicTask(Base):
    __tablename__='academic_tasks'
    __table_args__=(UniqueConstraint('user_id','event_key'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    topic_id:Mapped[int]=mapped_column(ForeignKey('curriculum_nodes.id'))
    quiz_id:Mapped[int|None]=mapped_column(ForeignKey('quizzes.id',ondelete='SET NULL'))
    event_key:Mapped[str]=mapped_column(String(100))
    kind:Mapped[str]=mapped_column(String(30))
    due_date:Mapped[date|None]=mapped_column(Date)
    completed_at:Mapped[datetime|None]=mapped_column(DateTime)
    estimated_minutes:Mapped[int]=mapped_column(Integer,default=30)
