from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserResponse


class ReviewCreate(BaseModel):
    """
    Schema for creating a review.
    Field(ge=1, le=5) means: rating must be >= 1 AND <= 5.
    Pydantic validates this automatically — if someone sends rating=10,
    they'll get a 422 error.
    """

    book_id: int
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    comment: str | None = None


class ReviewResponse(BaseModel):
    """Schema for review responses."""

    id: int
    user_id: int
    book_id: int
    rating: int
    comment: str | None = None
    created_at: datetime

    # Include the reviewer's name so the frontend can display it
    user: UserResponse

    model_config = {"from_attributes": True}


class BookRatingResponse(BaseModel):
    """
    Summary of a book's ratings — used for displaying
    average rating and total review count.
    """

    book_id: int
    average_rating: float
    total_reviews: int
