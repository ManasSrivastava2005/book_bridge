from datetime import datetime

from pydantic import BaseModel

from app.schemas.book import BookResponse
from app.schemas.user import UserResponse


class BorrowCreate(BaseModel):
    """
    Schema for borrowing a book.

    The student only needs to provide the book_id.
    Everything else (user_id, dates, status) is set automatically by the server.
    """

    book_id: int


class BorrowResponse(BaseModel):
    """
    Schema for borrow record responses.

    Includes nested user and book info so the frontend can display
    "Manas borrowed Harry Potter" without making extra API calls.
    """

    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None = None
    status: str
    issued_by: int | None = None

    # Nested objects — the full user and book details
    user: UserResponse
    book: BookResponse

    model_config = {"from_attributes": True}
