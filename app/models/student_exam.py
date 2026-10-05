from datetime import date
from sqlalchemy import Integer,String,Date,ForeignKey,CheckConstraint,JSON
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class StudentExam(Base):
    __tablename__='student_exams'
    __table_args__=(CheckConstraint('(subject_id IS NOT NULL AND custom_subject IS NULL) OR (subject_id IS NULL AND custom_subject IS NOT NULL)'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    subject_id:Mapped[int|None]=mapped_column(ForeignKey('curriculum_nodes.id'))
    custom_subject:Mapped[str|None]=mapped_column(String(150))
    name:Mapped[str]=mapped_column(String(150))
    exam_type:Mapped[str]=mapped_column(String(30))
    date:Mapped[date]=mapped_column(Date)
    topic_ids:Mapped[list|None]=mapped_column(JSON,nullable=True)
