from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.library import Library
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.review import Review

from app.database import get_db
from app.dependencies import require_role
from app.models.book import Book
from app.schemas.book import BookCreate, BookResponse, BookUpdate

# Create a router for book-related endpoints.
# 'prefix="/books"' means all endpoints here start with /books
# 'tags=["Books"]' groups them together in the /docs page
router = APIRouter(prefix="/books", tags=["Books"])


# ──────────────────────────────────────────────
# CREATE — POST /books
# ──────────────────────────────────────────────
@router.post(
    "/",
    response_model=BookResponse,
    status_code=201,
    dependencies=[Depends(require_role("librarian", "admin"))],
)
def create_book(book_data: BookCreate, db: Session = Depends(get_db)):
    """
    Add a new book to the library.

    How it works:
    1. 'book_data: BookCreate' — FastAPI automatically reads the JSON body
       and validates it against our BookCreate schema.
       If the title is missing, FastAPI returns a 422 error automatically!

    2. 'db: Session = Depends(get_db)' — FastAPI calls get_db() to give us
       a database session. 'Depends' is FastAPI's dependency injection system.
       Think of it as: "before running this function, get me a DB session."

    3. We create a Book model, add it to the session, commit (save), and
       refresh (reload from DB to get the auto-generated id and created_at).
    """
    if book_data.isbn:
        existing_book = db.query(Book).filter(Book.isbn == book_data.isbn).first()
        if existing_book:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A book with this ISBN already exists",
            )

    if book_data.library_id is not None and not db.get(Library, book_data.library_id):
        raise HTTPException(422, 'Library not found')
    new_book = Book(**book_data.model_dump())
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book


# ──────────────────────────────────────────────
# READ ALL — GET /books
# ──────────────────────────────────────────────
@router.get("/", response_model=list[BookResponse])
def get_all_books(db: Session = Depends(get_db)):
    """
    Get a list of all books in the library.

    'response_model=list[BookResponse]' tells FastAPI:
    "The response will be a LIST of BookResponse objects."
    """
    books = db.query(Book).all()
    return books


# ──────────────────────────────────────────────
# READ ONE — GET /books/{book_id}
# ──────────────────────────────────────────────
@router.get("/discover")
def discover_books(db: Session = Depends(get_db)):
    """Real historical popularity; zero means no recorded borrowing or ratings."""
    from sqlalchemy import func
    loans=dict(db.query(BorrowRecord.book_id,func.count(BorrowRecord.id)).group_by(BorrowRecord.book_id).all())
    ratings={row[0]:(float(row[1]),row[2]) for row in db.query(Review.book_id,func.avg(Review.rating),func.count(Review.id)).group_by(Review.book_id)}
    libraries={row.id:row for row in db.query(Library).all()}
    result=[]
    for book in db.query(Book).order_by(Book.created_at.desc(),Book.id.desc()):
        library=libraries.get(book.library_id)
        average,count=ratings.get(book.id,(None,0))
        result.append({**BookResponse.model_validate(book).model_dump(),'borrow_count':loans.get(book.id,0),'average_rating':round(average,1) if average is not None else None,'review_count':count,
                       'library_name':library.name if library else None,'library_campus':library.campus if library else None})
    return result


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    """
    Get a single book by its ID.

    '{book_id}' in the URL is a PATH PARAMETER.
    If someone visits /books/3, then book_id = 3.

    If the book doesn't exist, we raise an HTTPException with a 404 status
    (404 = "Not Found").
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


# ──────────────────────────────────────────────
# UPDATE — PUT /books/{book_id}
# ──────────────────────────────────────────────
@router.put(
    "/{book_id}",
    response_model=BookResponse,
    dependencies=[Depends(require_role("librarian", "admin"))],
)
def update_book(
    book_id: int, book_data: BookUpdate, db: Session = Depends(get_db)
):
    """
    Update an existing book's details.

    Only updates the fields that the user actually sent (non-None values).
    For example, if they only send {"title": "New Title"}, only the title
    changes — author, isbn, etc. stay the same.
    """
    book = db.query(Book).filter(Book.id == book_id).with_for_update().first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # model_dump(exclude_unset=True) gives us ONLY the fields the user sent.
    # This prevents accidentally overwriting existing values with None.
    update_data = book_data.model_dump(exclude_unset=True)

    if "isbn" in update_data and update_data["isbn"]:
        existing_book = (
            db.query(Book)
            .filter(Book.isbn == update_data["isbn"], Book.id != book_id)
            .first()
        )
        if existing_book:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A book with this ISBN already exists",
            )

    if update_data.get('library_id') is not None and not db.get(Library, update_data['library_id']):
        raise HTTPException(422, 'Library not found')
    if 'total_copies' in update_data and 'available_copies' not in update_data:
        update_data['available_copies'] = book.available_copies + update_data['total_copies'] - book.total_copies
    new_total_copies = update_data.get("total_copies", book.total_copies)
    new_available_copies = update_data.get("available_copies", book.available_copies)
    active = db.query(BorrowRecord).filter(BorrowRecord.book_id == book_id, BorrowRecord.status == 'borrowed').count()
    held = db.query(Reservation).filter(Reservation.book_id == book_id, Reservation.status == 'ready').count()
    if new_available_copies < 0 or new_total_copies - new_available_copies < active + held:
        raise HTTPException(409, 'Inventory must retain a copy for every active loan and held reservation.')
    if update_data.get('library_id', book.library_id) != book.library_id and active + held:
        raise HTTPException(409, 'Return active loans and resolve held reservations before transferring this book.')
    if new_available_copies > new_total_copies:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="available_copies cannot be greater than total_copies",
        )

    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


# ──────────────────────────────────────────────
# DELETE — DELETE /books/{book_id}
# ──────────────────────────────────────────────
@router.delete(
    "/{book_id}",
    status_code=204,
    dependencies=[Depends(require_role("librarian", "admin"))],
)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """
    Delete a book from the library.

    status_code=204 means "No Content" — the deletion was successful,
    but there's nothing to send back.
    """
    book = db.query(Book).filter(Book.id == book_id).with_for_update().first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    for model in (BorrowRecord, Reservation, Review):
        if db.query(model).filter(model.book_id == book_id).first():
            raise HTTPException(409, 'This book has borrowing, reservation, or review history and cannot be deleted.')
    db.delete(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'This book is referenced by other records and cannot be deleted.')
    return None


# ──────────────────────────────────────────────
# SEARCH — GET /books/search/?query=harry
# ──────────────────────────────────────────────
@router.get("/search/", response_model=list[BookResponse])
def search_books(query: str, db: Session = Depends(get_db)):
    """
    Search books by title, author, or category.

    'query: str' is a QUERY PARAMETER.
    Example: /books/search/?query=harry
    FastAPI reads 'query' from the URL automatically.

    'ilike' is case-insensitive LIKE search.
    '%' is a wildcard — '%harry%' matches "Harry Potter", "When Harry Met..."
    """
    books = (
        db.query(Book)
        .filter(
            Book.title.ilike(f"%{query}%")
            | Book.author.ilike(f"%{query}%")
            | Book.category.ilike(f"%{query}%")
        )
        .all()
    )
    return books
