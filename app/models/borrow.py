from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BorrowRecord(Base):
    """
    The BorrowRecord model — represents the 'borrow_records' table.

    Tracks who borrowed which book, when, and whether it's been returned.

    Key columns:
    - user_id: WHO borrowed (foreign key → users table)
    - book_id: WHAT was borrowed (foreign key → books table)
    - borrowed_at: WHEN it was borrowed
    - due_date: WHEN it should be returned
    - returned_at: WHEN it was actually returned (None if still borrowed)
    - status: "borrowed" or "returned"
    """

    __tablename__ = "borrow_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FOREIGN KEYS — these link this record to the users and books tables.
    # ForeignKey("users.id") means: "this column stores a value that must
    # exist in the 'id' column of the 'users' table."
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"), nullable=False)

    issued_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    request_key: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timestamps
    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="borrowed")

    # RELATIONSHIPS — these let us access the related User and Book objects
    # directly from a BorrowRecord object.
    # Example: borrow_record.user.name → gives you the borrower's name
    #          borrow_record.book.title → gives you the book's title
    # These don't create new columns — they're just convenient Python shortcuts.
    user = relationship("User", foreign_keys=[user_id])
    book = relationship("Book")
