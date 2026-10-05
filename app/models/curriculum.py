from datetime import datetime
from sqlalchemy import Integer, String, Boolean, ForeignKey, UniqueConstraint, CheckConstraint, DateTime, func, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Curriculum(Base):
    __tablename__='curricula'
    __table_args__=(UniqueConstraint('family','version'),UniqueConstraint('owner_user_id','semester',name='uq_personal_curriculum_semester'))
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    owner_user_id: Mapped[int|None]=mapped_column(ForeignKey('users.id'),nullable=True)
    family: Mapped[str]=mapped_column(String(36))
    version: Mapped[int]=mapped_column(Integer,default=1)
    title: Mapped[str]=mapped_column(String(200))
    college: Mapped[str]=mapped_column(String(200))
    program: Mapped[str]=mapped_column(String(120))
    branch: Mapped[str]=mapped_column(String(120))
    specialization: Mapped[str|None]=mapped_column(String(120))
    semester: Mapped[int]=mapped_column(Integer)
    archived: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime,server_default=func.now())

class CurriculumNode(Base):
    """Typed subject/unit/topic tree, with hierarchy enforced by staff service."""
    __tablename__='curriculum_nodes'
    __table_args__=(CheckConstraint("kind IN ('subject','unit','topic')"),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    curriculum_id: Mapped[int]=mapped_column(ForeignKey('curricula.id'),index=True)
    parent_id: Mapped[int|None]=mapped_column(ForeignKey('curriculum_nodes.id'))
    kind: Mapped[str]=mapped_column(String(20))
    title: Mapped[str]=mapped_column(String(200))
    code: Mapped[str|None]=mapped_column(String(50))
    objectives: Mapped[str|None]=mapped_column(Text,nullable=True)
    subtopics: Mapped[list|None]=mapped_column(JSON,nullable=True)
    archived: Mapped[bool]=mapped_column(Boolean,default=False,server_default='false')
    position: Mapped[int]=mapped_column(Integer,default=0)

class CurriculumResource(Base):
    __tablename__='curriculum_resources'
    __table_args__=(UniqueConstraint('topic_id','book_id'),UniqueConstraint('topic_id','digital_resource_id'),
                   UniqueConstraint('topic_id','note_id'),UniqueConstraint('topic_id','question_bank_id'),
                   CheckConstraint('(CASE WHEN book_id IS NULL THEN 0 ELSE 1 END + CASE WHEN digital_resource_id IS NULL THEN 0 ELSE 1 END + CASE WHEN note_id IS NULL THEN 0 ELSE 1 END + CASE WHEN question_bank_id IS NULL THEN 0 ELSE 1 END) = 1'))
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    topic_id: Mapped[int]=mapped_column(ForeignKey('curriculum_nodes.id'),index=True)
    book_id: Mapped[int|None]=mapped_column(ForeignKey('books.id'))
    digital_resource_id: Mapped[int|None]=mapped_column(ForeignKey('digital_resources.id'))
    note_id: Mapped[int|None]=mapped_column(ForeignKey('notes.id'))
    question_bank_id: Mapped[int|None]=mapped_column(ForeignKey('question_banks.id'))

class SubjectEnrollment(Base):
    __tablename__='subject_enrollments'
    __table_args__=(UniqueConstraint('user_id','subject_id'),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    subject_id: Mapped[int]=mapped_column(ForeignKey('curriculum_nodes.id'))
