from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.book import Book
from app.models.reservation import Reservation
from app.models.user import User
from app.models.borrow import BorrowRecord
from app.models.notification import Notification
from datetime import datetime, timezone
from app.schemas.reservation import ReservationCreate, ReservationResponse

router = APIRouter(prefix="/reservations", tags=["Reservations"])


# ──────────────────────────────────────────────
# RESERVE A BOOK — POST /reservations/
# ──────────────────────────────────────────────
@router.post("/", response_model=ReservationResponse, status_code=201)
def reserve_book(
    data: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """
    Reserve a book that has no available copies.

    Logic:
    1. Book must exist
    2. Book must have 0 available copies (if copies are available, just borrow it!)
    3. User must not already have a pending reservation for this book
    """
    book = db.query(Book).filter(Book.id == data.book_id).with_for_update().first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    # Only allow reservations when no copies are available
    if book.available_copies > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book is currently available — visit the library for staff checkout",
        )

    # Check for an existing active reservation. A fulfilled reservation means
    # a copy is already being held for this user and must be checked out.
    existing = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == current_user.id,
            Reservation.book_id == data.book_id,
            Reservation.status.in_(("pending", "ready")),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active reservation for this book",
        )

    if db.query(BorrowRecord).filter_by(user_id=current_user.id,book_id=data.book_id,status='borrowed').first():
        raise HTTPException(409,'You already have an active loan for this book')
    from app.services.circulation import eligible
    eligible(db,current_user,book)
    reservation = Reservation(
        user_id=current_user.id,
        book_id=data.book_id,
        status="pending",
    )
    db.add(reservation)
    db.add(Notification(user_id=current_user.id,message=f'Reservation pending: {book.title}.',is_read=False))
    db.commit()
    db.refresh(reservation)
    return reservation


# ──────────────────────────────────────────────
# MY RESERVATIONS — GET /reservations/my
# ──────────────────────────────────────────────
@router.get("/my", response_model=list[ReservationResponse])
def get_my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's reservations."""
    reservations = (
        db.query(Reservation)
        .filter(Reservation.user_id == current_user.id)
        .order_by(Reservation.created_at.desc())
        .all()
    )
    return reservations


# ──────────────────────────────────────────────
# CANCEL RESERVATION — DELETE /reservations/{id}
# ──────────────────────────────────────────────
@router.delete("/{reservation_id}", status_code=204)
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending reservation. Only the owner can cancel."""
    reservation = (
        db.query(Reservation).filter(Reservation.id == reservation_id).first()
    )
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found",
        )

    if (
        reservation.user_id != current_user.id
        and current_user.role.value not in ("librarian", "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own reservations",
        )

    if current_user.role.value in ('librarian','admin'):
        from app.services.circulation import process_reservation
        process_reservation(db,current_user,reservation_id,'cancel')
        return None
    # Serialize queue changes with checkouts and returns for this book.
    db.query(Book).filter(Book.id == reservation.book_id).with_for_update().first()
    db.refresh(reservation, with_for_update=True)
    if reservation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending reservations can be cancelled",
        )

    reservation.status = "cancelled"
    reservation.cancelled_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(Notification(user_id=reservation.user_id,message="Your reservation was cancelled.",is_read=False))
    db.commit()
    return None


# ──────────────────────────────────────────────
# VIEW QUEUE — GET /reservations/book/{book_id}
# ──────────────────────────────────────────────
@router.get("/book/{book_id}", response_model=list[ReservationResponse])
def get_book_reservations(
    book_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("librarian", "admin")),
):
    """
    View the reservation queue for a specific book (librarian/admin only).
    Ordered by created_at — first come, first served.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    reservations = (
        db.query(Reservation)
        .filter(Reservation.book_id == book_id, Reservation.status == "pending")
        .order_by(Reservation.created_at.asc())
        .all()
    )
    return reservations
