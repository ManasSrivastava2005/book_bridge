from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.models.book import Book
from app.models.digital_resource import DigitalResource
from app.models.note import Note
from app.models.question_bank import QuestionBank

router = APIRouter(prefix="/search", tags=["Unified Search"])


@router.get("/unified")
def unified_search(
    query: str = Query(..., min_length=1),
    resource_type: str = Query("all", description="all, book, ebook, note, question_bank"),
    library_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Search across physical books, online e-books, lecture notes, and question banks.
    Returns categorized and unified results with unambiguous availability indicators.
    """
    results = {
        "query": query,
        "total_results": 0,
        "books": [],
        "digital_resources": [],
        "notes": [],
        "question_banks": [],
    }

    q = f"%{query}%"

    # 1. Physical Books
    if resource_type in ("all", "book", "physical"):
        b_query = db.query(Book).filter(
            Book.title.ilike(q) | Book.author.ilike(q) | Book.category.ilike(q)
        )
        if library_id:
            b_query = b_query.filter(Book.library_id == library_id)
        for b in b_query.limit(10).all():
            results["books"].append({
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "category": b.category,
                "rack": b.rack or "A",
                "shelf": b.shelf or "1",
                "available_copies": b.available_copies,
                "total_copies": b.total_copies,
                "is_available": b.available_copies > 0,
                "cover_image": b.cover_image,
                "type": "physical_book",
                "link": f"/books/{b.id}",
            })

    # 2. Digital E-Books
    if resource_type in ("all", "ebook", "digital"):
        d_query = db.query(DigitalResource).filter(
            DigitalResource.is_published == True, DigitalResource.archived_at.is_(None), DigitalResource.reviewed_by.isnot(None),
            (DigitalResource.title.ilike(q) | DigitalResource.author.ilike(q) | DigitalResource.subject.ilike(q))
        )
        if library_id:
            d_query = d_query.filter(DigitalResource.library_id == library_id)
        for d in d_query.limit(10).all():
            results["digital_resources"].append({
                "id": d.id,
                "title": d.title,
                "author": d.author,
                "provider": d.provider,
                "resource_type": d.resource_type,
                "access_type": d.access_type,
                "cover_image": d.cover_image,
                "type": "online_ebook",
                "link": f"/reader/{d.id}",
                "external_url": d.external_url,
            })

    # 3. Notes Library
    if resource_type in ("all", "note", "notes"):
        n_query = db.query(Note).filter(
            Note.status == "published",
            (Note.title.ilike(q) | Note.subject.ilike(q) | Note.description.ilike(q))
        )
        if library_id:
            n_query = n_query.filter(Note.library_id == library_id)
        for n in n_query.limit(10).all():
            results["notes"].append({
                "id": n.id,
                "title": n.title,
                "subject": n.subject,
                "semester": n.semester,
                "branch": n.branch,
                "file_type": n.file_type,
                "file_size": n.file_size,
                "type": "note",
                "link": f"/notes",
            })

    # 4. Question Banks
    if resource_type in ("all", "question_bank", "exam"):
        qb_query = db.query(QuestionBank).filter(
            QuestionBank.title.ilike(q) | QuestionBank.subject.ilike(q) | QuestionBank.branch.ilike(q)
        )
        if library_id:
            qb_query = qb_query.filter(QuestionBank.library_id == library_id)
        for qb in qb_query.limit(10).all():
            results["question_banks"].append({
                "id": qb.id,
                "title": qb.title,
                "subject": qb.subject,
                "semester": qb.semester,
                "exam_type": qb.exam_type,
                "academic_year": qb.academic_year,
                "type": "question_bank",
                "link": f"/question-banks",
            })

    results["total_results"] = (
        len(results["books"])
        + len(results["digital_resources"])
        + len(results["notes"])
        + len(results["question_banks"])
    )
    return results
