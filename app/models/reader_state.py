"""Private per-account document state; independent of shared Notes permissions."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ReaderState(Base):
    __tablename__ = 'reader_states'
    __table_args__ = (UniqueConstraint('user_id', 'resource_id', name='uq_reader_user_resource'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey('digital_resources.id', ondelete='CASCADE'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
