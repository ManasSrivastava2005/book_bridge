"""A daily delivery key prevents duplicate overdue notifications."""
from datetime import date
from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class OverdueReminder(Base):
    __tablename__='overdue_reminders'
    borrow_id: Mapped[int]=mapped_column(ForeignKey('borrow_records.id',ondelete='CASCADE'),primary_key=True)
    day: Mapped[date]=mapped_column(Date,primary_key=True)
    notification_id: Mapped[int]=mapped_column(ForeignKey('notifications.id',ondelete='CASCADE'),nullable=False)
