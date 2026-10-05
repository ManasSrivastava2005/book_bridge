import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.protected_uploads import ProtectedUploads

from app.config import CORS_ORIGINS
from app.database import Base, engine

# Import all models to ensure metadata registration
from app.models.user import User  # noqa: F401
from app.models.book import Book  # noqa: F401
from app.models.borrow import BorrowRecord  # noqa: F401
from app.models.reservation import Reservation  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.search_history import SearchHistory  # noqa: F401
from app.models.badge import Badge, UserBadge  # noqa: F401
from app.models.reading_activity import ReadingActivity  # noqa: F401
from app.models.library import Library  # noqa: F401
from app.models.digital_resource import DigitalResource  # noqa: F401
from app.models.note import Note  # noqa: F401
from app.models.question_bank import QuestionBank  # noqa: F401
from app.models.reader_state import ReaderState  # noqa: F401

from app.models.study import StudyRoom, StudyMember, StudyMessage  # noqa: F401

from app.models.overdue_reminder import OverdueReminder  # noqa: F401
from app.models.loan_renewal import LoanRenewal  # noqa: F401

from app.models.contribution import Contribution, ContributionAudit, XPTransaction

from app.models.curriculum import Curriculum, CurriculumNode, CurriculumResource, SubjectEnrollment

from app.models.quiz import Quiz, QuizQuestion

from app.models.announcement import Announcement, AnnouncementDelivery

from app.models.resource_usage import ResourceUsage

from app.models.reading_session import ReadingSession, ReadingDay

from app.models.academic_profile import AcademicProfile

from app.models.topic_progress import TopicProgress

from app.models.student_exam import StudentExam

from app.models.academic_task import AcademicTask
from app.models.syllabus_upload import SyllabusUpload

from app.models.quiz_attempt import QuizAttempt

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Book Bridge API",
    description="Smart Digital Library Management Platform (v2.0.0)",
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file uploads serving
uploads_dir = Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", ProtectedUploads(directory=str(uploads_dir)), name="uploads")

# Import and register routers
from app.routers import (
    auth, users, books, borrows, reservations, reviews,
    notifications, dashboard, admin, ai, book_summarization,
    libraries, digital_resources, notes, question_banks, unified_search, reader, study
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(books.router)
app.include_router(borrows.router)
app.include_router(reservations.router)
app.include_router(reviews.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(ai.router)
app.include_router(book_summarization.router)
app.include_router(libraries.router)
app.include_router(digital_resources.router)
app.include_router(notes.router)
app.include_router(question_banks.router)
app.include_router(unified_search.router)
app.include_router(reader.router)
app.include_router(study.router)
from app.routers import renewals
app.include_router(renewals.router)
from app.routers import contributions
app.include_router(contributions.router)
from app.routers import curriculum
app.include_router(curriculum.router)
from app.routers import quizzes
app.include_router(quizzes.router)
from app.routers import announcements, staff_users, student_data, personal_curriculum, syllabus
app.include_router(announcements.router)
app.include_router(staff_users.router)
app.include_router(student_data.router)
app.include_router(personal_curriculum.router)
app.include_router(syllabus.router)
from app.routers import insights
app.include_router(insights.router)
from app.routers import scanner
app.include_router(scanner.router)
from app.routers import xp
app.include_router(xp.router)
from app.routers import reading_activity
app.include_router(reading_activity.router)
from app.routers import badges
app.include_router(badges.router)
from app.routers import leaderboard
app.include_router(leaderboard.router)
from app.routers import academic
app.include_router(academic.router)
from app.routers import student_exams
app.include_router(student_exams.router)
from app.routers import curriculum_workspace
app.include_router(curriculum_workspace.router)
from app.routers import student_quizzes
app.include_router(student_quizzes.router)
from app.routers import student_contributions
app.include_router(student_contributions.router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Book Bridge API",
        "tagline": "Read â€¢ Learn â€¢ Grow",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}

from app.routers import staff_profile
app.include_router(staff_profile.router)
