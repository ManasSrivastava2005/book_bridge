from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.book import Book
from app.models.digital_resource import DigitalResource
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.library import Library

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

class ChatRequest(BaseModel):
    query: Optional[str] = None
    message: Optional[str] = None

class SummarizeRequest(BaseModel):
    text: str

@router.post("/chat")
def chat_with_library_ai(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_prompt = (req.query or req.message or "").strip()
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Empty query provided")

    q = user_prompt.lower()

    # 1. Search physical books
    books = db.query(Book).all()
    matching_books = [
        b for b in books
        if b.title.lower() in q or any(word in b.title.lower() for word in q.split() if len(word) > 3)
    ]

    # 2. Search digital e-books
    ebooks = db.query(DigitalResource).filter(DigitalResource.is_published == True, DigitalResource.archived_at.is_(None), DigitalResource.reviewed_by.isnot(None)).all()
    matching_ebooks = [
        e for e in ebooks
        if e.title.lower() in q or (e.subject and e.subject.lower() in q) or (e.category and e.category.lower() in q)
    ]

    # 3. Search notes
    notes = db.query(Note).filter(Note.status == "published").all()
    matching_notes = [
        n for n in notes
        if (n.subject and n.subject.lower() in q) or (n.title and n.title.lower() in q)
    ]

    # 4. Search question banks
    qbs = db.query(QuestionBank).all()
    matching_qbs = [
        qb for qb in qbs
        if (qb.subject and qb.subject.lower() in q) or ("question" in q or "exam" in q or "paper" in q)
    ]

    # Generate grounded catalog-aware response
    if "where" in q or "find" in q or "rack" in q or "shelf" in q or "location" in q:
        if matching_books:
            b = matching_books[0]
            status_str = f"Currently {b.available_copies} of {b.total_copies} copies are available." if b.available_copies > 0 else "All physical copies are currently borrowed (you can reserve it via dashboard)."
            reply = (
                f"📍 You can find '{b.title}' by {b.author} in Rack {b.rack or 'A'}, Shelf {b.shelf or '1'} "
                f"at the Central Campus Library. {status_str}"
            )
        else:
            reply = (
                "Physical books in our library are organized systematically: Computer Science & Programming is in Rack A, "
                "Systems & Networking in Rack B, and Mathematics & Core Engineering in Rack C. "
                "Check the Browse Books section or use our barcode/QR shelf locator."
            )

    elif "ebook" in q or "e-book" in q or "online" in q or "read online" in q:
        if matching_ebooks:
            e = matching_ebooks[0]
            reply = (
                f"📖 Yes! '{e.title}' is available online via {e.provider} ({e.access_type} access). "
                f"You can read it directly in our embedded online reader under the E-Books tab!"
            )
        else:
            reply = (
                "We provide open-access e-books through Project Gutenberg, DOAB, and MIT OpenCourseWare. "
                "Explore the 'E-Books & Resources' section in the sidebar to read verified textbooks online."
            )

    elif "note" in q or "lecture" in q or "syllabus" in q:
        if matching_notes:
            n = matching_notes[0]
            reply = (
                f"📝 Found notes for you: '{n.title}' for {n.subject} (Semester {n.semester}, {n.branch}). "
                f"It is available for immediate download or preview in the Notes Library."
            )
        else:
            reply = (
                "Our Notes Library contains verified semester lecture notes, formula sheets, and study materials "
                "for Computer Science & Engineering. You can filter by subject and semester in the Notes Library."
            )

    elif "question bank" in q or "exam" in q or "previous year" in q or "mid term" in q or "end term" in q:
        if matching_qbs:
            qb = matching_qbs[0]
            reply = (
                f"📑 Available question paper: '{qb.title}' ({qb.exam_type}, {qb.academic_year}) for {qb.subject}. "
                f"Includes {qb.total_questions} questions with official answer rubrics in the Question Bank section."
            )
        else:
            reply = (
                "You can access previous years' mid-term and end-term exam question papers with answer keys "
                "in the Question Bank section in the navigation menu."
            )

    elif matching_books:
        b = matching_books[0]
        reply = (
            f"Yes, '{b.title}' by {b.author} is in our collection (Rack {b.rack or 'A'}, Shelf {b.shelf or '1'}). "
            f"Availability: {b.available_copies}/{b.total_copies} copies in stock."
        )

    elif "python" in q:
        reply = (
            "For Python, we have 'Clean Code' principles, and our open-access e-book 'Think Python' by Allen Downey. "
            "Physical reference copies are located on Shelf A-2."
        )

    elif "dsa" in q or "data structure" in q:
        reply = (
            "For Data Structures & Algorithms, we have curated lecture notes and a 100-problem Practice Question Set in the Question Bank! "
            "Learning path milestones: Arrays -> Linked Lists -> Stacks -> Trees & Graphs -> Dynamic Programming."
        )

    else:
        reply = (
            f"I checked the Book Bridge catalog for '{user_prompt}'. We currently have physical textbooks across Rack A-C, "
            f"open-access e-books (SICP, Think Python, OSTEP), and comprehensive semester notes in the library."
        )

    return {
        "query": user_prompt,
        "response": reply,
        "answer": reply,
        "user": current_user.name
    }

@router.post("/summarize")
def summarize_text(req: SummarizeRequest):
    words = req.text.split()
    summary = " ".join(words[:min(len(words), 50)]) + "..."
    return {"summary": f"Key takeaway: {summary}"}
