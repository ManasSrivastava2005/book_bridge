from app.database import engine
from app.models.library import Library
from app.models.user import User
from app.models.curriculum import Curriculum
from app.models.academic_profile import AcademicProfile

def migrate(connection):AcademicProfile.__table__.create(connection,checkfirst=True)
if __name__=='__main__':
    with engine.begin() as connection:migrate(connection)
    print('Optional academic profile migration complete.')
