"""Create only the additive private syllabus upload table."""
def migrate(connection):
    from app.models.user import User
    from app.models.curriculum import Curriculum
    from app.models.syllabus_upload import SyllabusUpload
    SyllabusUpload.__table__.create(connection,checkfirst=True)
