from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Contribution(Base):
    __tablename__='contributions'
    __table_args__=(UniqueConstraint('user_id','request_key',name='uq_contribution_request'),CheckConstraint("status IN ('PENDING','APPROVED','REJECTED')"),
                   CheckConstraint("kind IN ('note','question_paper','question_bank','study_material')"))
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    title: Mapped[str]=mapped_column(String(255))
    kind: Mapped[str]=mapped_column(String(30))
    subject: Mapped[str]=mapped_column(String(100))
    course_code: Mapped[str|None]=mapped_column(String(50))
    semester: Mapped[int|None]=mapped_column(Integer)
    branch: Mapped[str|None]=mapped_column(String(100))
    exam_type: Mapped[str|None]=mapped_column(String(50))
    academic_year: Mapped[str|None]=mapped_column(String(20))
    college: Mapped[str|None]=mapped_column(String(200))
    storage_name: Mapped[str]=mapped_column(String(64),unique=True)
    original_name: Mapped[str]=mapped_column(String(180))
    request_key: Mapped[str|None]=mapped_column(String(36))
    payload_hash: Mapped[str|None]=mapped_column(String(64))
    status: Mapped[str]=mapped_column(String(20),default='PENDING',index=True)
    rejection_reason: Mapped[str|None]=mapped_column(Text)
    reviewer_id: Mapped[int|None]=mapped_column(ForeignKey('users.id'))
    note_id: Mapped[int|None]=mapped_column(ForeignKey('notes.id'))
    question_bank_id: Mapped[int|None]=mapped_column(ForeignKey('question_banks.id'))
    created_at: Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
    reviewed_at: Mapped[datetime|None]=mapped_column(DateTime)

class ContributionAudit(Base):
    __tablename__='contribution_audit'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    contribution_id: Mapped[int]=mapped_column(ForeignKey('contributions.id'),unique=True)
    staff_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    decision: Mapped[str]=mapped_column(String(20))
    reason: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime,server_default=func.now())

class XPTransaction(Base):
    __tablename__='xp_transactions'
    __table_args__=(CheckConstraint('amount > 0'),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    event_key: Mapped[str]=mapped_column(String(150),unique=True)
    amount: Mapped[int]=mapped_column(Integer)
    event_type: Mapped[str]=mapped_column(String(30),default="CONTRIBUTION",server_default="CONTRIBUTION")
    description: Mapped[str]=mapped_column(String(255),default="Approved contribution",server_default="Approved contribution")
    created_at: Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
