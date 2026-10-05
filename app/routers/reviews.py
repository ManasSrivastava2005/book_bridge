from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.review import Review
from app.models.user import User
from app.schemas.review import BookRatingResponse, ReviewCreate, ReviewResponse

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def has_borrowing_history(db,user_id,book_id):
    return db.query(BorrowRecord.id).filter(BorrowRecord.user_id==user_id,BorrowRecord.book_id==book_id,BorrowRecord.status.in_(('borrowed','returned'))).first() is not None

@router.get('/book/{book_id}/eligibility')
def review_eligibility(book_id:int,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    if not db.get(Book,book_id):raise HTTPException(404,'Book not found')
    eligible=has_borrowing_history(db,user.id,book_id)
    return {'eligible':eligible,'reason':None if eligible else 'Reviews require a recorded loan for this book.'}


# ──────────────────────────────────────────────
# ADD A REVIEW — POST /reviews/
# ──────────────────────────────────────────────
@router.post("/", response_model=ReviewResponse, status_code=201)
def create_review(
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """
    Add a review for a book.

    Rules:
    1. Book must exist
    2. One review per user per book (can't review the same book twice)
    3. Rating must be 1-5 (Pydantic validates this automatically)
    """
    book = db.query(Book).filter(Book.id == data.book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    # Serialize per-student review upserts, preserving existing legacy reviews.
    db.query(User).filter_by(id=current_user.id).with_for_update().one()
    if not has_borrowing_history(db,current_user.id,data.book_id):
        raise HTTPException(403,'Reviews require a recorded loan for this book.')

    # Check if user already reviewed this book — if so, update their existing review
    existing = (
        db.query(Review)
        .filter(
            Review.user_id == current_user.id,
            Review.book_id == data.book_id,
        )
        .first()
    )
    if existing:
        existing.rating = data.rating
        existing.comment = data.comment
        db.commit()
        db.refresh(existing)
        return existing

    review = Review(
        user_id=current_user.id,
        book_id=data.book_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


# ──────────────────────────────────────────────
# GET REVIEWS FOR A BOOK — GET /reviews/book/{book_id}
# ──────────────────────────────────────────────
@router.get("/book/{book_id}", response_model=list[ReviewResponse])
def get_book_reviews(book_id: int, db: Session = Depends(get_db)):
    """
    Get all reviews for a specific book.
    Public endpoint — anyone can view reviews.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    reviews = (
        db.query(Review)
        .filter(Review.book_id == book_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return reviews


# ──────────────────────────────────────────────
# GET AVERAGE RATING — GET /reviews/book/{book_id}/rating
# ──────────────────────────────────────────────
@router.get("/book/{book_id}/rating", response_model=BookRatingResponse)
def get_book_rating(book_id: int, db: Session = Depends(get_db)):
    """
    Get the average rating and total review count for a book.

    Uses SQL aggregate functions (AVG, COUNT) via SQLAlchemy.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    result = (
        db.query(
            func.avg(Review.rating).label("average_rating"),
            func.count(Review.id).label("total_reviews"),
        )
        .filter(Review.book_id == book_id)
        .first()
    )

    return BookRatingResponse(
        book_id=book_id,
        average_rating=round(float(result.average_rating or 0), 1),
        total_reviews=result.total_reviews,
    )


# ──────────────────────────────────────────────
# DELETE A REVIEW — DELETE /reviews/{review_id}
# ──────────────────────────────────────────────
@router.delete("/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete your own review. Librarians/admins can delete any review."""
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if (
        review.user_id != current_user.id
        and current_user.role.value not in ("librarian", "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews",
        )

    db.delete(review)
    db.commit()
    return None
