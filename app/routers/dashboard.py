from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.review import Review
from app.models.reading_activity import ReadingActivity
from app.models.badge import UserBadge

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Reading activity
    activity = db.query(ReadingActivity).filter(ReadingActivity.user_id == current_user.id).first()
    
    # Count badges
    badge_count = db.query(UserBadge).filter(UserBadge.user_id == current_user.id).count()
    
    # Active borrows
    active_borrows = db.query(BorrowRecord).filter(
        BorrowRecord.user_id == current_user.id,
        BorrowRecord.status == "borrowed"
    ).count()
    
    # Total books read (returned borrows)
    books_read = db.query(BorrowRecord).filter(
        BorrowRecord.user_id == current_user.id,
        BorrowRecord.status == "returned"
    ).count()
    
    # Reviews written
    reviews_written = db.query(Review).filter(Review.user_id == current_user.id).count()
    
    from app.services.xp import reader_level
    level_data = reader_level(db, current_user.id)
    xp = level_data["current_level_xp"]
    level = level_data["level"]
    from app.routers.reading_activity import streak_data
    streak = streak_data(db, current_user.id)["current_streak"]
    
    # XP required for next level (simple formula: level * 200)
    xp_required = level * 200
    
    from app.services.missions import daily_missions
    missions = daily_missions(db, current_user.id)

    return {
        **level_data,
        "reader_level": level,
        "xp": xp,
        "xp_required": xp_required,
        "reading_streak": streak,
        "books_read": books_read,
        "badges_unlocked": badge_count,
        "active_borrows": active_borrows,
        "missions": missions,
    }


@router.get("/activity")
def get_recent_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get recent borrows and reviews
    recent_borrows = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.user_id == current_user.id)
        .order_by(BorrowRecord.borrowed_at.desc())
        .limit(5)
        .all()
    )
    
    recent_reviews = (
        db.query(Review)
        .filter(Review.user_id == current_user.id)
        .order_by(Review.created_at.desc())
        .limit(5)
        .all()
    )
    
    activities = []
    for b in recent_borrows:
        book = db.query(Book).filter(Book.id == b.book_id).first()
        title = book.title if book else "Unknown"
        if b.status == "borrowed":
            activities.append({
                "type": "borrow", 
                "description": f"You borrowed {title}",
                "timestamp": b.borrowed_at.isoformat()
            })
        else:
            activities.append({
                "type": "return",
                "description": f"You returned {title}",
                "timestamp": (b.returned_at or b.borrowed_at).isoformat()
            })
    
    for r in recent_reviews:
        book = db.query(Book).filter(Book.id == r.book_id).first()
        title = book.title if book else "Unknown"
        activities.append({
            "type": "review",
            "description": f"You wrote a review for {title}",
            "timestamp": r.created_at.isoformat()
        })
    
    # Sort by timestamp descending
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:10]


@router.get("/recommended")
def get_recommended_books(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.services.recommendations import recommendations
    return recommendations(db,current_user)


@router.get("/student-progress")
def student_progress(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.quiz_attempt import QuizAttempt
    from app.models.contribution import Contribution
    from app.routers.reading_activity import streak_data
    from app.services.student_curriculum import curriculum_data
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == current_user.id, QuizAttempt.submitted_at.is_not(None))
    return {
        **streak_data(db, current_user.id),
        "books_read": db.query(func.count(func.distinct(BorrowRecord.book_id))).filter(BorrowRecord.user_id == current_user.id, BorrowRecord.status == "returned").scalar(),
        "completed_quizzes": attempts.count(),
        "average_quiz_score": attempts.with_entities(func.avg(QuizAttempt.score)).scalar(),
        "approved_contributions": db.query(Contribution).filter_by(user_id=current_user.id, status="APPROVED").count(),
        "subjects": [{k: s[k] for k in ("id", "title", "completed_topics", "total_topics", "progress_percent")} for s in curriculum_data(db, current_user.id)["subjects"]],
    }
