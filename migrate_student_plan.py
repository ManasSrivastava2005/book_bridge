from app.database import engine
from app.models.library import Library
from app.models.user import User
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.book import Book
from app.models.quiz import Quiz
from app.models.academic_task import AcademicTask

def migrate(connection):AcademicTask.__table__.create(connection,checkfirst=True)
if __name__=='__main__':
    with engine.begin() as connection:migrate(connection)
    print('Academic task migration complete.')
