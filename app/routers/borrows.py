from app.services.badges import award_badges
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.borrow import BorrowCreate, BorrowResponse

router = APIRouter(prefix="/borrows", tags=["Borrows"])

# Default loan period in days
LOAN_PERIOD_DAYS = 14


# ──────────────────────────────────────────────
# BORROW A BOOK — POST /borrows/
# ──────────────────────────────────────────────
@router.post("/", response_model=BorrowResponse, status_code=201)
def borrow_book(borrow_data: BorrowCreate, db: Session = Depends(get_db),
                current_user: User = Depends(require_role("librarian", "admin"))):
    raise HTTPException(403, "Use staff circulation to select a student and record an issue")

@router.post("/{borrow_id}/return", response_model=BorrowResponse)
def return_book(borrow_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(require_role("librarian", "admin"))):
    from app.services.circulation import return_loan
    return return_loan(db, current_user, borrow_id)


# ──────────────────────────────────────────────
# MY BORROWS — GET /borrows/my
# ──────────────────────────────────────────────
@router.get("/my", response_model=list[BorrowResponse])
def get_my_borrows(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the current user's borrow history.

    Shows all books they've borrowed (both active and returned).
    """
    borrows = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.user_id == current_user.id)
        .order_by(BorrowRecord.borrowed_at.desc())
        .all()
    )
    return borrows


# ──────────────────────────────────────────────
# ALL BORROWS — GET /borrows/ (Librarian/Admin only)
# ──────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[BorrowResponse],
    dependencies=[Depends(require_role("librarian", "admin"))],
)
def get_all_borrows(db: Session = Depends(get_db)):
    """
    Get ALL borrow records (librarian/admin only).

    Useful for librarians to see who has what book and track overdue books.
    """
    borrows = (
        db.query(BorrowRecord)
        .order_by(BorrowRecord.borrowed_at.desc())
        .all()
    )
    return borrows
