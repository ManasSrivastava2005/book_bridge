from datetime import datetime, date
from sqlalchemy import Integer, String, DateTime, Date, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ReadingSession(Base):
    __tablename__ = 'reading_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey('digital_resources.id'))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_ping: Mapped[datetime] = mapped_column(DateTime)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    last_page: Mapped[int] = mapped_column(Integer, default=1)
    page_seconds: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

class ReadingDay(Base):
    __tablename__ = 'reading_days'
    __table_args__ = (UniqueConstraint('user_id', 'date'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    date: Mapped[date] = mapped_column(Date)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    pages: Mapped[list] = mapped_column(JSON, default=list)
