"""
FastAPI Router for Book QR Code Generation & Real-Time Physical Scanning Workflow.
Queries PostgreSQL for live book status, exact physical Rack/Shelf location, and queue status.
"""
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.reservation import Reservation
from app.services.qr_service import (
    generate_book_qr_bytes,
    generate_printable_book_sticker,
    get_qr_base64,
    get_sticker_base64,
)

router = APIRouter(tags=["QR & Physical Scanner"])


class ScanRequest(BaseModel):
    scanned_payload: str = Field(min_length=1,max_length=4000)


# ──────────────────────────────────────────────
# 1. GET BOOK QR CODE (PNG Image)
# ──────────────────────────────────────────────
@router.get("/books/{book_id}/qr", summary="Get Raw Scannable QR Code Image", dependencies=[Depends(require_role("librarian","admin"))])
def get_book_qr_code(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Generate and stream a PNG QR Code image for the given Book ID.
    Encodes unique book identification and backend scan URL.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    base_url = str(request.base_url).rstrip("/")
    img_bytes = generate_book_qr_bytes(book_id, base_url)
    return Response(content=img_bytes, media_type="image/png")


# ──────────────────────────────────────────────
# 2. GET PRINTABLE BOOK STICKER (PNG Image)
# ──────────────────────────────────────────────
@router.get("/books/{book_id}/sticker", summary="Get Printable Physical Book Sticker Label", dependencies=[Depends(require_role("librarian","admin"))])
def get_printable_sticker_label(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Generate and stream a formatted physical sticker label ready for printing
    and attaching to physical library books.
    Includes Rack, Shelf, Title, Author, and QR Code.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    base_url = str(request.base_url).rstrip("/")
    sticker = generate_printable_book_sticker(book, base_url)
    buffer = io.BytesIO()
    sticker.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


# ──────────────────────────────────────────────
# 3. GET QR & STICKER DATA (Base64 JSON)
# ──────────────────────────────────────────────
@router.get("/books/{book_id}/qr/data", summary="Get Base64 QR & Sticker Data for Web UI", dependencies=[Depends(require_role("librarian","admin"))])
def get_book_qr_data(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get Base64 encoded images of both raw QR code and physical sticker
    for rapid rendering in web modals without additional network requests.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    base_url = str(request.base_url).rstrip("/")
    qr_b64 = get_qr_base64(book_id, base_url)
    sticker_b64 = get_sticker_base64(book, base_url)

    return {
        "book_id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "rack": book.rack or "Not recorded",
        "shelf": book.shelf or "Not recorded",
        "qr_base64": qr_b64,
        "sticker_base64": sticker_b64,
        "scan_url": f"{base_url}/books/{book.id}/scan",
    }


# ──────────────────────────────────────────────
# 4. SCANNING WORKFLOW — GET /books/{book_id}/scan
# ──────────────────────────────────────────────
@router.get("/scan/{book_id}", include_in_schema=False)
@router.get("/books/{book_id}/scan", summary="Physical Scan Workflow: Query PostgreSQL by Book ID")
def scan_book_workflow(
    book_id: int,
    db: Session = Depends(get_db),
):
    """
    Execute the physical book scanning workflow:
    1. Query PostgreSQL for Book record
    2. Extract physical Rack & Shelf location
    3. Calculate real-time available vs issued stock
    4. Query active borrow records and earliest expected return date
    5. Query pending reservation queue
    6. Return navigation path and action suggestions
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scanned Book ID #{book_id} was not found in the library database."
        )

    now = datetime.now(timezone.utc)
    total_copies = book.total_copies or 1
    available_copies = book.available_copies if book.available_copies is not None else total_copies
    issued_copies = db.query(BorrowRecord).filter(BorrowRecord.book_id==book.id,BorrowRecord.status=="borrowed").count()

    # Active borrows
    active_borrows = (
        db.query(BorrowRecord)
        .filter(
            BorrowRecord.book_id == book.id,
            BorrowRecord.status == "borrowed",
        )
        .order_by(BorrowRecord.due_date.asc())
        .all()
    )

    earliest_due_date = None
    if active_borrows and active_borrows[0].due_date:
        earliest_due_date = active_borrows[0].due_date.isoformat()

    # Pending reservations
    pending_reservations_count = (
        db.query(func.count(Reservation.id))
        .filter(
            Reservation.book_id == book.id,
            Reservation.status == "pending",
        )
        .scalar()
        or 0
    )

    # Status Determination
    if available_copies > 1:
        stock_status = "AVAILABLE"
        status_label = f"Available ({available_copies} copies ready on shelf)"
        status_color = "emerald"
    elif available_copies == 1:
        stock_status = "LOW_STOCK"
        status_label = "Last Copy Available on Shelf"
        status_color = "amber"
    else:
        stock_status = "OUT_OF_STOCK"
        status_label = "No copies currently available"
        status_color = "rose"

    issued_copies = len(active_borrows)
    rack = book.rack or "Not recorded"
    shelf = book.shelf or "Not recorded"

    # Location Navigation Guidance
    location_guide = {
        "rack": rack,
        "shelf": shelf,
        "zone": f"Zone {rack.split('-')[0].replace('Rack ', '') if '-' in rack else 'General'}",
        "navigation_path": f"Main Library -> {rack} -> {shelf}",
        "shelf_level": int(re.sub(r"\D", "", shelf)) if re.sub(r"\D", "", shelf) else 1,
    }

    return {
        "scanned_at": now.isoformat(),
        "book": {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "category": book.category or "General",
            "description": book.description,
            "total_copies": total_copies,
            "available_copies": available_copies,
            "issued_copies": issued_copies,
        },
        "location": location_guide,
        "availability": {
            "status": stock_status,
            "status_label": status_label,
            "status_color": status_color,
            "can_borrow": available_copies > 0,
            "can_reserve": available_copies == 0,
            "active_loans_count": len(active_borrows),
            "earliest_due_date": earliest_due_date,
            "pending_reservations_count": pending_reservations_count,
        },
        "action_prompt": (
            f"Physical copy is located at {rack} • {shelf}. Ready for checkout."
            if available_copies > 0
            else f"No physical copies on shelf. Earliest return expected: {earliest_due_date or 'Not recorded'}. Reserve queue: {pending_reservations_count} students."
        ),
    }


# ──────────────────────────────────────────────
# 5. RESOLVE SCANNED RAW PAYLOAD (Scanner Utility)
# ──────────────────────────────────────────────
@router.post("/scan/resolve", summary="Resolve Scanned Barcode/QR Code String")
def resolve_scanned_code(
    payload_data: ScanRequest,
    db: Session = Depends(get_db),
):
    """
    Parse any scanned barcode string, QR JSON, or URL and resolve to live book data.
    Supports:
    - Raw ID: "3" or "#3"
    - JSON payload: '{"app":"BookBridge","book_id":3}'
    - Scan URL: "http://127.0.0.1:8000/scan/3" or "http://127.0.0.1:8000/books/3/scan"
    - ISBN: "9780136042594"
    """
    raw = payload_data.scanned_payload.strip()

    def resolve_id(value):
        if isinstance(value,bool) or not str(value).isdigit() or not 0 < int(value) <= 2147483647:
            raise HTTPException(400,'Invalid book ID')
        return scan_book_workflow(int(value),db)
    try:
        data=json.loads(raw)
    except (ValueError,TypeError):
        data=None
    if isinstance(data,dict):
        value=data.get('book_id',data.get('id'))
        if value is not None:return resolve_id(value)
    url_match=re.search(r'/(?:scan|books)/(\d+)(?:/scan)?(?:[/?#]|$)',raw)
    if url_match:return resolve_id(url_match.group(1))
    if re.fullmatch(r'#?\d{1,9}',raw):return resolve_id(raw.lstrip('#'))
    isbn=re.sub(r'[-\s]','',raw).upper()
    if re.fullmatch(r'(?:\d{13}|\d{9}[\dX])',isbn):
        book=db.query(Book).filter(Book.isbn==isbn).first()
        if book:return scan_book_workflow(book.id,db)
        raise HTTPException(404,'ISBN not found in the library catalogue')
    raise HTTPException(400,'Use a Book Bridge QR payload, book ID, scan URL, or ISBN')
