"""Create only the three Study Together tables; never alter existing tables."""
from app.database import engine
from app.models.library import Library
from app.models.user import User
from app.models.study import StudyRoom, StudyMember, StudyMessage, StudyAudit, StudyReport, StudyAttachment


def migrate(bind=engine):
    for model in (StudyRoom, StudyMember, StudyMessage, StudyAudit, StudyReport, StudyAttachment):
        model.__table__.create(bind=bind, checkfirst=True)


if __name__ == '__main__':
    migrate()
    print('Study Together tables ready; existing tables and records preserved.')
