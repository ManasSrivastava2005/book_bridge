"""Add remaining-feature tables and optional private-room columns; preserve old data."""
from sqlalchemy import inspect, text
from app.database import engine
from app.models.library import Library
from app.models.user import User
from app.models.book import Book
from app.models.borrow import BorrowRecord
from app.models.notification import Notification
from app.models.overdue_reminder import OverdueReminder
from app.models.study import StudyRoom, StudyAudit, StudyReport, StudyAttachment


def migrate(bind):
    columns={column['name'] for column in inspect(bind).get_columns('study_rooms')}
    if 'is_private' not in columns:
        bind.execute(text('ALTER TABLE study_rooms ADD COLUMN is_private BOOLEAN NOT NULL DEFAULT false'))
    if 'invite_code' not in columns:
        bind.execute(text('ALTER TABLE study_rooms ADD COLUMN invite_code VARCHAR(64)'))
    for model in (OverdueReminder,StudyAudit,StudyReport,StudyAttachment):
        model.__table__.create(bind=bind,checkfirst=True)


if __name__=='__main__':
    with engine.begin() as connection:migrate(connection)
    print('Remaining-feature migration complete; existing records preserved.')
