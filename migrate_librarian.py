"""Add librarian tables without dropping or rewriting existing records."""
from app.database import engine, Base
from app.models.library import Library
from app.models.user import User
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.loan_renewal import LoanRenewal

from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.contribution import Contribution, ContributionAudit, XPTransaction

from app.models.digital_resource import DigitalResource
from app.models.curriculum import Curriculum, CurriculumNode, CurriculumResource, SubjectEnrollment

from app.models.quiz import Quiz, QuizQuestion

from app.models.notification import Notification
from app.models.announcement import Announcement, AnnouncementDelivery

from app.models.resource_usage import ResourceUsage

def migrate(connection):
    for model in (LoanRenewal, Contribution, ContributionAudit, XPTransaction, Curriculum, CurriculumNode, CurriculumResource, SubjectEnrollment, Quiz, QuizQuestion, Announcement, AnnouncementDelivery, ResourceUsage):
        model.__table__.create(connection, checkfirst=True)

if __name__ == '__main__':
    with engine.begin() as connection: migrate(connection)
    print('Librarian migration complete; existing records preserved.')
