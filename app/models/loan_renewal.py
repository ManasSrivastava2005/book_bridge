from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class LoanRenewal(Base):
    __tablename__ = 'loan_renewals'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    borrow_id: Mapped[int] = mapped_column(ForeignKey('borrow_records.id'), index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    old_due_date: Mapped[datetime] = mapped_column(DateTime)
    new_due_date: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
