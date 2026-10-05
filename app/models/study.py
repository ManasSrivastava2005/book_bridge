"""Study Together rooms; independent of private reader and Notes data."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class StudyRoom(Base):
    __tablename__ = 'study_rooms'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', nullable=False)
    invite_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StudyMember(Base):
    __tablename__ = 'study_members'
    room_id: Mapped[int] = mapped_column(ForeignKey('study_rooms.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    role: Mapped[str] = mapped_column(String(20), default='MEMBER', server_default='MEMBER', nullable=False)


class StudyMessage(Base):
    __tablename__ = 'study_messages'
    __table_args__ = (
        UniqueConstraint('room_id', 'user_id', 'client_id', name='uq_study_message_retry'),
        Index('ix_study_message_room_id', 'room_id', 'id'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('study_rooms.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    client_id: Mapped[str] = mapped_column(String(36), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    reply_to_id: Mapped[int | None] = mapped_column(ForeignKey('study_messages.id'), nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StudyAudit(Base):
    __tablename__ = 'study_audit'
    __table_args__ = (Index('ix_study_audit_rate', 'actor_id', 'action', 'created_at'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('study_rooms.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default='', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StudyReport(Base):
    __tablename__ = 'study_reports'
    __table_args__ = (UniqueConstraint('message_id', 'reporter_id', name='uq_study_report_author'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('study_rooms.id', ondelete='CASCADE'), nullable=False)
    message_id: Mapped[int | None] = mapped_column(ForeignKey('study_messages.id', ondelete='SET NULL'), nullable=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class StudyAttachment(Base):
    __tablename__ = 'study_attachments'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('study_rooms.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    filename: Mapped[str] = mapped_column(String(180), nullable=False)
    storage_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
