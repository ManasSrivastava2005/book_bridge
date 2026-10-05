from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Reservation(Base):
    """
    The Reservation model — represents the 'reservations' table.

    When a book has no available copies, a student can RESERVE it.
    Reservations are served in order (first come, first served) using
    the 'created_at' timestamp as the queue position.

    Statuses:
    - "pending": waiting for a copy to become available
    - "ready": a copy is held for pickup
    - "fulfilled": staff issued the copy and linked its loan
    - "cancelled": the student cancelled their reservation
    """

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("books.id"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), default="pending")

    loan_id: Mapped[int | None] = mapped_column(ForeignKey("borrow_records.id"), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships for easy access
    user = relationship("User")
    book = relationship("Book")
