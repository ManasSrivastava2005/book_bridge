from app.database import engine
from app.models.library import Library
from app.models.user import User
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.topic_progress import TopicProgress

def migrate(connection):TopicProgress.__table__.create(connection,checkfirst=True)
if __name__=='__main__':
    with engine.begin() as connection:migrate(connection)
    print('Topic progress migration complete.')
