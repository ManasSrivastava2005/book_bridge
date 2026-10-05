"""Staff-controlled physical circulation with preserved queue history."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.models.user import User, UserRole
from app.models.book import Book
from app.models.library import Library
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.notification import Notification

def now():return datetime.now(timezone.utc).replace(tzinfo=None)

def staff_only(actor):
    if actor.role.value not in ('librarian','admin'):raise HTTPException(403,'Physical circulation must be recorded by library staff')

def notify(db,user_id,message):db.add(Notification(user_id=user_id,message=message,is_read=False))

def eligible(db,student,book,library_id=None):
    if library_id is not None and book.library_id!=library_id:raise HTTPException(422,'Book does not belong to the selected library')
    if book.library_id is not None:
        library=db.get(Library,book.library_id)
        if not library or not library.is_active:raise HTTPException(409,'The issuing library is inactive')
        if student.library_id!=book.library_id:raise HTTPException(403,'Assign the student to this library before issuing its books')

def issue(db,actor,student_id,book_id,due_date=None,library_id=None,request_key=None):
    staff_only(actor)
    student=db.query(User).filter_by(id=student_id,role=UserRole.STUDENT).with_for_update().first()
    if not student:raise HTTPException(404,'Student not found')
    book=db.query(Book).filter_by(id=book_id).with_for_update().first()
    if not book:raise HTTPException(404,'Book not found')
    due=due_date.astimezone(timezone.utc).replace(tzinfo=None) if due_date and due_date.tzinfo else due_date
    digest=hashlib.sha256(json.dumps([student_id,book_id,library_id,due.isoformat() if due else None]).encode()).hexdigest()
    if request_key:
        previous=db.query(BorrowRecord).filter_by(request_key=str(request_key)).first()
        if previous:
            if previous.issued_by!=actor.id or previous.request_hash!=digest:raise HTTPException(409,'Checkout request already used for a different transaction')
            return previous
    eligible(db,student,book,library_id)
    due=due or now()+timedelta(days=14)
    if due<=now() or due>now()+timedelta(days=366):raise HTTPException(422,'Choose a future due date within one year')
    if db.query(BorrowRecord).filter_by(user_id=student_id,book_id=book_id,status='borrowed').first():
        raise HTTPException(409,'Student already has an active loan for this book')
    held=db.query(Reservation).filter_by(user_id=student_id,book_id=book_id,status='ready').first()
    if not held:
        first=db.query(Reservation).filter_by(book_id=book_id,status='pending').order_by(Reservation.created_at,Reservation.id).first()
        if first and first.user_id!=student_id:raise HTTPException(409,'Serve the reservation queue before issuing this copy')
        if book.available_copies<=0:raise HTTPException(409,'No copy is available for this student')
        book.available_copies-=1
        held=first
    loan=BorrowRecord(user_id=student_id,book_id=book_id,due_date=due,status='borrowed',issued_by=actor.id,
                      request_key=str(request_key) if request_key else None,request_hash=digest if request_key else None)
    db.add(loan)
    try:
        db.flush()
        if held:
            held.status='fulfilled';held.loan_id=loan.id;held.fulfilled_at=now()
        notify(db,student_id,f'Book issued: {book.title}. Due {due.date().isoformat()}.')
        from app.services.badges import award_badges
        award_badges(db,student_id)
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Checkout changed concurrently; refresh before retrying') from None
    db.refresh(loan);return loan

def waiting(db,book_id):
    return db.query(Reservation).filter_by(book_id=book_id,status='pending').order_by(Reservation.created_at,Reservation.id).first()

def hand_available_copy(db,book):
    row=waiting(db,book.id)
    if row:
        row.status='ready';row.ready_at=now()
        notify(db,row.user_id,f'Your reservation for {book.title} is ready for pickup.')
    else:book.available_copies+=1

def return_loan(db,actor,loan_id):
    staff_only(actor)
    loan=db.get(BorrowRecord,loan_id)
    if not loan:raise HTTPException(404,'Loan not found')
    book=db.query(Book).filter_by(id=loan.book_id).with_for_update().one()
    db.refresh(loan,with_for_update=True)
    if loan.status=='returned':return loan
    loan.status='returned';loan.returned_at=now()
    hand_available_copy(db,book)
    notify(db,loan.user_id,f'Return recorded: {book.title}.')
    db.commit();db.refresh(loan);return loan

def process_reservation(db,actor,reservation_id,action):
    staff_only(actor)
    row=db.get(Reservation,reservation_id)
    if not row:raise HTTPException(404,'Reservation not found')
    book=db.query(Book).filter_by(id=row.book_id).with_for_update().one()
    db.refresh(row,with_for_update=True)
    if action=='ready':
        if row.status=='ready':return row
        if row.status!='pending':raise HTTPException(409,'Only pending reservations can be prepared')
        first=waiting(db,book.id)
        if not first or first.id!=row.id:raise HTTPException(409,'Serve the oldest reservation first')
        if book.available_copies<=0:raise HTTPException(409,'No copy is available yet')
        book.available_copies-=1;row.status='ready';row.ready_at=now()
        notify(db,row.user_id,f'Your reservation for {book.title} is ready for pickup.')
    elif action=='cancel':
        if row.status=='cancelled':return row
        if row.status not in ('pending','ready'):raise HTTPException(409,'This reservation is no longer active')
        was_ready=row.status=='ready';row.status='cancelled';row.cancelled_at=now();db.flush()
        if was_ready:hand_available_copy(db,book)
        notify(db,row.user_id,f'Your reservation for {book.title} was cancelled.')
    else:raise HTTPException(422,'Unsupported reservation action')
    db.commit();db.refresh(row);return row
