from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.borrow import BorrowRecord
from app.models.book import Book
from app.models.reservation import Reservation
from app.models.user import User
from app.models.loan_renewal import LoanRenewal
from app.config import LOAN_RENEWAL_DAYS, LOAN_MAX_RENEWALS

router = APIRouter(prefix='/admin/loans', tags=['Loan renewals'], dependencies=[Depends(require_role('librarian','admin'))])

class RenewRequest(BaseModel):
    request_id: UUID
    expected_due_date: datetime

@router.get('/{borrow_id}/renewals')
def history(borrow_id: int, db: Session = Depends(get_db)):
    if not db.get(BorrowRecord, borrow_id): raise HTTPException(404, 'Loan not found')
    return db.query(LoanRenewal).filter(LoanRenewal.borrow_id == borrow_id).order_by(LoanRenewal.id).all()

@router.post('/{borrow_id}/renew')
def renew(borrow_id: int, payload: RenewRequest, db: Session = Depends(get_db),
          staff: User = Depends(require_role('librarian','admin'))):
    loan = db.get(BorrowRecord, borrow_id)
    if not loan: raise HTTPException(404, 'Loan not found')
    db.query(Book).filter(Book.id == loan.book_id).with_for_update().one()
    db.refresh(loan, with_for_update=True)
    existing = db.query(LoanRenewal).filter(LoanRenewal.request_id == str(payload.request_id)).first()
    if existing:
        if existing.borrow_id != borrow_id: raise HTTPException(409, 'Request belongs to another loan')
        return existing
    if loan.status != 'borrowed': raise HTTPException(409, 'Only active loans may be renewed')
    if loan.due_date != payload.expected_due_date.replace(tzinfo=None): raise HTTPException(409, 'Due date changed. Refresh this loan before renewing.')
    now = db.query(func.current_timestamp()).scalar().replace(tzinfo=None)
    if loan.due_date < now: raise HTTPException(409, 'Overdue loans must be returned before another checkout')
    if db.query(Reservation).filter(Reservation.book_id == loan.book_id, Reservation.user_id != loan.user_id,
                                     Reservation.status.in_(['pending','ready'])).first():
        raise HTTPException(409, 'Another student has a reservation for this book')
    count = db.query(LoanRenewal).filter(LoanRenewal.borrow_id == borrow_id).count()
    if count >= LOAN_MAX_RENEWALS: raise HTTPException(409, 'Renewal limit reached')
    record = LoanRenewal(borrow_id=borrow_id, staff_id=staff.id, request_id=str(payload.request_id),
                         old_due_date=loan.due_date, new_due_date=loan.due_date+timedelta(days=LOAN_RENEWAL_DAYS))
    loan.due_date=record.new_due_date;db.add(record);db.commit();db.refresh(record)
    return record
