from datetime import datetime

from pydantic import BaseModel

from app.schemas.book import BookResponse
from app.schemas.user import UserResponse


class ReservationCreate(BaseModel):
    """
    Schema for creating a reservation.
    Student only needs to say which book they want to reserve.
    """

    book_id: int


class ReservationResponse(BaseModel):
    """
    Schema for reservation responses.
    Includes nested user and book details.
    """

    id: int
    user_id: int
    book_id: int
    status: str
    created_at: datetime
    loan_id: int | None = None
    ready_at: datetime | None = None
    fulfilled_at: datetime | None = None
    cancelled_at: datetime | None = None

    user: UserResponse
    book: BookResponse

    model_config = {"from_attributes": True}
