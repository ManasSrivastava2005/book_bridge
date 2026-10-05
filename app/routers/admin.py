from datetime import datetime, timezone, timedelta
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, case
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import require_role
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.models.review import Review
from app.models.user import User, UserRole
from app.models.digital_resource import DigitalResource
from app.models.library import Library
from app.models.contribution import Contribution
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.schemas.digital_resource import DigitalResourceResponse, DigitalResourceCreate
from app.services.auth import hash_password
from app.services import ebook_storage
from app.schemas.user import UserResponse
from app.schemas.reservation import ReservationResponse
from app.schemas.borrow import BorrowCreate, BorrowResponse
from app.services import circulation
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter(prefix="/admin", tags=["Admin & Analytics"], dependencies=[Depends(require_role("librarian", "admin"))])


def database_now(db):
    # Legacy timestamp columns store database-local time without an offset.
    return db.query(func.current_timestamp()).scalar().replace(tzinfo=None)


class StaffCheckout(BaseModel):
    book_id: int = Field(gt=0)
    student_id: int = Field(gt=0)
    library_id: int | None = Field(None, gt=0)
    due_date: datetime | None = None
    request_id: UUID | None = None


@router.get('/catalog')
def staff_catalog(search: str = Query('', max_length=200), category: str = Query('', max_length=100),
                  library_id: int | None = Query(None, gt=0), page: int = Query(1, ge=1),
                  db: Session = Depends(get_db)):
    from app.schemas.book import BookResponse
    query = db.query(Book)
    if search.strip():
        term = '%' + search.strip() + '%'
        query = query.filter(Book.title.ilike(term) | Book.author.ilike(term) | Book.isbn.ilike(term))
    if category: query = query.filter(Book.category == category)
    if library_id: query = query.filter(Book.library_id == library_id)
    total = query.count()
    items = query.order_by(Book.created_at.desc(), Book.id.desc()).offset((page-1)*20).limit(20).all()
    return {'items': [BookResponse.model_validate(b).model_dump() for b in items], 'total': total,
            'page': page, 'page_size': 20,
            'categories': [r[0] for r in db.query(Book.category).filter(Book.category.isnot(None), Book.category != '').distinct().order_by(Book.category).all()]}


@router.get("/students", response_model=list[UserResponse])
def get_students(search: str = Query('',max_length=200), db: Session = Depends(get_db)):
    query=db.query(User).filter(User.role == UserRole.STUDENT)
    if search.strip():
        term='%'+search.strip()+'%'
        query=query.filter(User.name.ilike(term)|User.student_id.ilike(term)|User.email.ilike(term))
    return query.order_by(User.name,User.id).all()


@router.get("/overdue-books")
def get_overdue_books(db: Session = Depends(get_db)):
    loans = db.query(BorrowRecord).filter(BorrowRecord.status == 'borrowed', BorrowRecord.due_date < database_now(db)).order_by(BorrowRecord.due_date, BorrowRecord.id).all()
    return [{'borrow_id': loan.id, 'book_id': loan.book_id, 'book_title': loan.book.title,
             'student_name': loan.user.name, 'student_email': loan.user.email,
             'due_date': loan.due_date, 'user_id': loan.user_id} for loan in loans]


@router.get("/reservations", response_model=list[ReservationResponse])
def get_reservations(db: Session = Depends(get_db)):
    return db.query(Reservation).order_by(Reservation.created_at, Reservation.id).all()


@router.post("/loans", response_model=BorrowResponse, status_code=201)
def checkout_for_student(payload: StaffCheckout, db: Session = Depends(get_db), staff: User = Depends(require_role('librarian','admin'))):
    return circulation.issue(db,staff,payload.student_id,payload.book_id,payload.due_date,payload.library_id,payload.request_id)

@router.post('/reservations/{reservation_id}/release', response_model=ReservationResponse)
def release_held_reservation(reservation_id: int, db: Session = Depends(get_db), staff: User = Depends(require_role('librarian','admin'))):
    return circulation.process_reservation(db,staff,reservation_id,'cancel')

@router.post('/reservations/{reservation_id}/ready', response_model=ReservationResponse)
def prepare_reservation(reservation_id: int, db: Session = Depends(get_db), staff: User = Depends(require_role('librarian','admin'))):
    return circulation.process_reservation(db,staff,reservation_id,'ready')


@router.get('/digital-resources', response_model=list[DigitalResourceResponse])
def staff_resources(db: Session = Depends(get_db)):
    return db.query(DigitalResource).order_by(DigitalResource.created_at.desc(), DigitalResource.id.desc()).all()


@router.put('/digital-resources/{resource_id}', response_model=DigitalResourceResponse)
def edit_digital_resource(resource_id: int, payload: DigitalResourceCreate, db: Session = Depends(get_db), staff: User = Depends(require_role("librarian","admin"))):
    resource = db.get(DigitalResource, resource_id)
    if not resource:
        raise HTTPException(404, 'Digital resource not found')
    if payload.library_id is not None and not db.get(Library, payload.library_id):
        raise HTTPException(404, 'Library not found')
    if (resource.file_url or "").startswith("/uploads/") and payload.file_url != resource.file_url:
        raise HTTPException(422, "Keep the legacy file reference; upload a new resource and archive this one instead.")
    if ebook_storage.managed(resource.file_url) or ebook_storage.managed(payload.file_url):
        if payload.file_url != resource.file_url:
            raise HTTPException(422, 'Managed PDF file references cannot be reassigned. Upload a new resource instead.')
        ebook_storage.validate_managed_metadata(payload)
        if payload.resource_type != 'uploaded_pdf' or payload.external_url:
            raise HTTPException(422, 'Managed PDF resources must retain their PDF type and have no external URL.')
    if resource.archived_at is not None and payload.is_published:
        raise HTTPException(409, "Restore the archived resource to draft before publishing")
    for field, value in payload.model_dump().items():
        setattr(resource, field, value)
    resource.reviewed_by=None;resource.reviewed_at=None
    if resource.is_published:ebook_storage.record_review(resource,staff)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("/dashboard")
def get_admin_dashboard(db: Session = Depends(get_db)):
    """
    Get live metrics, popular books, and rule-based inventory indicators.
    """
    now = database_now(db)

    # 1. METRICS
    total_titles = db.query(func.count(Book.id)).scalar() or 0
    total_copies = db.query(func.sum(Book.total_copies)).scalar() or 0
    available_copies = db.query(func.sum(Book.available_copies)).scalar() or 0

    # Issued books
    issued_books_count = (
        db.query(func.count(BorrowRecord.id))
        .filter(BorrowRecord.status == "borrowed")
        .scalar()
        or 0
    )

    # Overdue books
    overdue_books_count = (
        db.query(func.count(BorrowRecord.id))
        .filter(
            BorrowRecord.status == "borrowed",
            BorrowRecord.due_date < now,
        )
        .scalar()
        or 0
    )

    # Total students
    total_students_count = (
        db.query(func.count(User.id))
        .filter(User.role == UserRole.STUDENT)
        .scalar()
        or 0
    )

    # Active reservations
    reservations_count = (
        db.query(func.count(Reservation.id))
        .filter(Reservation.status.in_(["pending", "ready"]))
        .scalar()
        or 0
    )

    # Group each relationship independently to avoid multiplying loans by reviews.
    loan_counts = {row.book_id: row for row in db.query(
        BorrowRecord.book_id, func.count(BorrowRecord.id).label("total"),
        func.sum(case((BorrowRecord.status == "borrowed", 1), else_=0)).label("active"),
    ).group_by(BorrowRecord.book_id).all()}
    waiting_counts = dict(db.query(Reservation.book_id, func.count(Reservation.id)).filter(
        Reservation.status == "pending").group_by(Reservation.book_id).all())
    ratings = {row.book_id: row for row in db.query(
        Review.book_id, func.avg(Review.rating).label("average"), func.count(Review.id).label("total"),
    ).group_by(Review.book_id).all()}
    popular_books = []
    for book in db.query(Book).order_by(Book.id).all():
        loans = loan_counts.get(book.id)
        reviews = ratings.get(book.id)
        borrow_count = loans.total if loans else 0
        active_borrows = loans.active if loans else 0
        pending_reservations = waiting_counts.get(book.id, 0)
        avg_rating = reviews.average if reviews else None
        review_count = reviews.total if reviews else 0

        popularity_score = (borrow_count * 3) + (pending_reservations * 4) + (float(avg_rating or 0) * 2)

        popular_books.append({
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "category": book.category or "General",
            "rack": book.rack,
            "shelf": book.shelf,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "borrow_count": borrow_count,
            "active_borrows": active_borrows,
            "pending_reservations": pending_reservations,
            "average_rating": round(float(avg_rating), 1) if avg_rating else 0.0,
            "review_count": review_count,
            "popularity_score": round(popularity_score, 1),
        })

    # Sort popular books by score descending
    popular_books.sort(key=lambda x: x["popularity_score"], reverse=True)

    # 3. Legacy demand fields: inventory heuristics, not trained predictions.
    demand_predictions = []
    for item in popular_books:
        tot = max(item["total_copies"], 1)
        avail = item["available_copies"]
        active = item["active_borrows"]
        res = item["pending_reservations"]
        utilization = (tot - avail) / tot

        predicted_30d = math.ceil(
            (active * 1.5) + (res * 2.0) + (item["borrow_count"] * 0.4) + (1.2 if utilization > 0.6 else 0.5)
        )

        if avail == 0 or (res > 0 and avail <= 1) or utilization >= 0.8:
            risk_level = "High Demand"
            risk_color = "red"
            suggested_action = f"Shortage Alert! Add +{max(2, res + 1)} copies urgently"
            shortage_probability = min(98, 70 + (res * 8))
        elif utilization >= 0.5 or res > 0:
            risk_level = "Moderate Demand"
            risk_color = "yellow"
            suggested_action = "Monitor stock; exam cycle surge expected"
            shortage_probability = min(75, 40 + (active * 6))
        else:
            risk_level = "Normal Demand"
            risk_color = "green"
            suggested_action = "Adequate inventory on shelf"
            shortage_probability = max(5, int(utilization * 30))

        demand_predictions.append({
            "book_id": item["id"],
            "title": item["title"],
            "category": item["category"],
            "rack_location": ' / '.join(str(value) for value in (item['rack'], item['shelf']) if value) or 'Not recorded',
            "current_available": avail,
            "total_copies": item['total_copies'],
            "utilization_pct": round(utilization * 100, 1),
            "pending_reservations": res,
            "predicted_checkouts_next_30d": predicted_30d,
            "shortage_probability": shortage_probability,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "suggested_action": suggested_action,
        })

    demand_predictions.sort(key=lambda x: (x["shortage_probability"], x["predicted_checkouts_next_30d"]), reverse=True)

    recent_borrows = (
        db.query(BorrowRecord)
        .options(joinedload(BorrowRecord.user), joinedload(BorrowRecord.book))
        .order_by(func.coalesce(BorrowRecord.returned_at, BorrowRecord.borrowed_at).desc(), BorrowRecord.id.desc())
        .limit(10)
        .all()
    )
    activities = []
    for b in recent_borrows:
        activities.append({
            "id": b.id,
            "type": "return" if b.status == "returned" else "borrow",
            "user_name": b.user.name if b.user else "Student",
            "book_title": b.book.title if b.book else "Book",
            "date": (b.returned_at or b.borrowed_at).isoformat() if b.borrowed_at else None,
            "status": b.status,
            "is_overdue": b.status == "borrowed" and b.due_date < now if b.due_date else False,
        })

    return {
        "metrics": {
            "total_books": total_titles,
            "total_copies": total_copies,
            "pending_contributions": db.query(Contribution).filter(Contribution.status == "PENDING").count(),
            "available_books": available_copies,
            "issued_books": issued_books_count,
            "overdue_books": overdue_books_count,
            "total_students": total_students_count,
            "reservations": reservations_count,
        },
        "recent_books": [{"id": b.id, "title": b.title, "author": b.author, "created_at": b.created_at} for b in db.query(Book).order_by(Book.created_at.desc(), Book.id.desc()).limit(5).all()],
        "popular_books": popular_books[:8],
        "demand_prediction": demand_predictions[:8],
        "demand_method": "inventory_heuristic",
        "recent_activities": activities,
    }


@router.get("/analytics")
def circulation_analytics(
    days: int = Query(30, ge=1, le=366),
    library_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db),
):
    """Calendar-day activity and current overdue ages, in the database time zone."""
    if library_id is not None and not db.get(Library, library_id):
        raise HTTPException(404, "Library not found")
    now = database_now(db)
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    scope = [Book.library_id == library_id] if library_id is not None else []

    def daily_counts(column, *conditions):
        day = func.date(column)
        rows = db.query(day, func.count(BorrowRecord.id)).join(Book).filter(
            *scope, column >= start, column <= now, *conditions,
        ).group_by(day).all()
        return {str(date): count for date, count in rows}

    checkouts = daily_counts(BorrowRecord.borrowed_at)
    returns = daily_counts(BorrowRecord.returned_at, BorrowRecord.status == "returned")
    daily = [{"date": (start + timedelta(days=offset)).date().isoformat(),
              "checkouts": checkouts.get((start + timedelta(days=offset)).date().isoformat(), 0),
              "returns": returns.get((start + timedelta(days=offset)).date().isoformat(), 0)}
             for offset in range(days)]
    borrowers = db.query(func.count(func.distinct(BorrowRecord.user_id))).join(Book).filter(
        *scope, BorrowRecord.borrowed_at >= start, BorrowRecord.borrowed_at <= now,
    ).scalar() or 0
    category = func.coalesce(func.nullif(func.trim(Book.category), ""), "Uncategorized")
    categories = db.query(category.label("category"), func.count(BorrowRecord.id).label("checkouts")).select_from(BorrowRecord).join(
        Book, Book.id == BorrowRecord.book_id,
    ).filter(*scope, BorrowRecord.borrowed_at >= start, BorrowRecord.borrowed_at <= now).group_by(
        category).order_by(func.count(BorrowRecord.id).desc(), category).limit(8).all()
    overdue = db.query(
        func.sum(case((BorrowRecord.due_date > now - timedelta(days=7), 1), else_=0)),
        func.sum(case(((BorrowRecord.due_date <= now - timedelta(days=7)) &
                       (BorrowRecord.due_date > now - timedelta(days=30)), 1), else_=0)),
        func.sum(case((BorrowRecord.due_date <= now - timedelta(days=30), 1), else_=0)),
    ).select_from(BorrowRecord).join(Book).filter(
        *scope, BorrowRecord.status == "borrowed", BorrowRecord.due_date < now,
    ).one()
    return {
        "period": {"days": days, "start": start.date().isoformat(), "end": now.date().isoformat(),
                   "as_of": now.isoformat(), "time_basis": "database_local", "library_id": library_id},
        "totals": {"checkouts": sum(row["checkouts"] for row in daily),
                   "returns": sum(row["returns"] for row in daily), "unique_borrowers": borrowers},
        "daily": daily,
        "categories": [{"category": row.category, "checkouts": row.checkouts} for row in categories],
        "overdue": [{"label": label, "count": int(count or 0)} for label, count in zip(
            ["Under 7 days", "7 to under 30 days", "30 days or more"], overdue)],
    }


@router.get("/metrics")
def get_admin_metrics_summary(db: Session = Depends(get_db)):
    """
    Get lightweight numeric counters for top-level cards.
    """
    now = database_now(db)
    total_books = db.query(func.count(Book.id)).scalar() or 0
    available_books = db.query(func.sum(Book.available_copies)).scalar() or 0
    issued_books = (
        db.query(func.count(BorrowRecord.id))
        .filter(BorrowRecord.status == "borrowed")
        .scalar()
        or 0
    )
    overdue_books = (
        db.query(func.count(BorrowRecord.id))
        .filter(
            BorrowRecord.status == "borrowed",
            BorrowRecord.due_date < now,
        )
        .scalar()
        or 0
    )
    total_students = (
        db.query(func.count(User.id))
        .filter(User.role == UserRole.STUDENT)
        .scalar()
        or 0
    )
    reservations = (
        db.query(func.count(Reservation.id))
        .filter(Reservation.status == "pending")
        .scalar()
        or 0
    )

    return {
        "total_books": total_books,
        "available_books": available_books,
        "issued_books": issued_books,
        "overdue_books": overdue_books,
        "total_students": total_students,
        "reservations": reservations,
    }


@router.post("/seed", dependencies=[Depends(require_role("admin"))])
def seed_sample_data(db: Session = Depends(get_db)):
    """
    Seed initial rich demonstration data (Admin, Students, Books with Racks/Shelves, Borrows, and Reservations).
    """
    if not db.query(User).filter(User.email == "admin@bookbridge.edu").first():
        admin = User(
            name="Library Admin",
            email="admin@bookbridge.edu",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
        )
        db.add(admin)

    if not db.query(User).filter(User.email == "librarian@bookbridge.edu").first():
        librarian = User(
            name="Chief Librarian",
            email="librarian@bookbridge.edu",
            hashed_password=hash_password("librarian123"),
            role=UserRole.LIBRARIAN,
        )
        db.add(librarian)

    student_samples = [
        ("Aarav Sharma", "aarav@student.com"),
        ("Manas Verma", "manas@student.com"),
        ("Priya Patel", "priya@student.com"),
        ("Rohan Iyer", "rohan@student.com"),
        ("Ananya Das", "ananya@student.com"),
    ]
    students = []
    for name, email in student_samples:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name=name,
                email=email,
                hashed_password=hash_password("student123"),
                role=UserRole.STUDENT,
            )
            db.add(user)
            db.flush()
        students.append(user)

    sample_books = [
        {
            "title": "Artificial Intelligence: A Modern Approach",
            "author": "Stuart Russell & Peter Norvig",
            "isbn": "9780136042594",
            "category": "Computer Science",
            "rack": "Rack CS-01",
            "shelf": "Shelf 3",
            "total_copies": 5,
            "available_copies": 1,
            "description": "Comprehensive textbook covering modern search, knowledge representation, and probabilistic reasoning.",
        },
        {
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "author": "Robert C. Martin",
            "isbn": "9780132350884",
            "category": "Software Engineering",
            "rack": "Rack SE-02",
            "shelf": "Shelf 1",
            "total_copies": 4,
            "available_copies": 0,
            "description": "Best practices for writing readable, maintainable, and robust software architectures.",
        },
        {
            "title": "Deep Learning with Python",
            "author": "François Chollet",
            "isbn": "9781617294433",
            "category": "Machine Learning",
            "rack": "Rack ML-04",
            "shelf": "Shelf 2",
            "total_copies": 3,
            "available_copies": 2,
            "description": "Hands-on guide to deep neural networks and Keras implementation.",
        },
        {
            "title": "Database System Concepts",
            "author": "Abraham Silberschatz & Henry F. Korth",
            "isbn": "9780073523323",
            "category": "Databases",
            "rack": "Rack DB-01",
            "shelf": "Shelf 4",
            "total_copies": 6,
            "available_copies": 3,
            "description": "Foundational concepts of relational databases, indexing, and transaction management.",
        },
        {
            "title": "Introduction to Algorithms (CLRS)",
            "author": "Thomas H. Cormen",
            "isbn": "9780262033848",
            "category": "Algorithms",
            "rack": "Rack AL-03",
            "shelf": "Shelf 2",
            "total_copies": 8,
            "available_copies": 1,
            "description": "Standard university reference for sorting, graph algorithms, dynamic programming, and complexity.",
        },
        {
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "isbn": "9781449373320",
            "category": "System Design",
            "rack": "Rack SD-05",
            "shelf": "Shelf 1",
            "total_copies": 4,
            "available_copies": 2,
            "description": "The definitive guide to distributed systems, replication, partitioning, and stream processing.",
        },
    ]

    for bdata in sample_books:
        book = db.query(Book).filter(Book.isbn == bdata["isbn"]).first()
        if not book:
            book = Book(**bdata)
            db.add(book)

    db.commit()
    return {"message": "Database successfully seeded with realistic library records and physical locations!"}


class ResourceLifecycle(BaseModel):
    action: Literal['publish','unpublish','archive','restore']

@router.patch('/digital-resources/{resource_id}/lifecycle', response_model=DigitalResourceResponse)
def resource_lifecycle(resource_id: int, payload: ResourceLifecycle, db: Session = Depends(get_db), staff: User = Depends(require_role("librarian","admin"))):
    resource = db.query(DigitalResource).filter_by(id=resource_id).with_for_update().first()
    if not resource: raise HTTPException(404, 'Digital resource not found')
    if payload.action == 'publish':
        if resource.archived_at is not None: raise HTTPException(409, 'Restore this resource before publishing')
        if not resource.file_url and not resource.external_url: raise HTTPException(422, 'Add a readable file before publishing')
        if ebook_storage.managed(resource.file_url):
            ebook_storage.validate_managed_metadata(resource)
            if not (ebook_storage.PRIVATE_EBOOK_DIR / resource.file_url.rsplit('/',1)[-1]).is_file():
                raise HTTPException(409, 'The uploaded file is missing; publication was not changed')
        ebook_storage.record_review(resource,staff)
        resource.is_published = True
    elif payload.action == 'archive':
        resource.is_published = False
        resource.archived_at = resource.archived_at or datetime.now(timezone.utc).replace(tzinfo=None)
    elif payload.action == 'restore':
        resource.archived_at = None
        resource.is_published = False
    else:
        resource.is_published = False
    db.commit();db.refresh(resource)
    return resource
