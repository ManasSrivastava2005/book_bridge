from app.database import engine
from app.models.library import Library
from app.models.user import User
from app.models.digital_resource import DigitalResource
from app.models.reading_session import ReadingSession, ReadingDay

def migrate(connection):
    for model in (ReadingSession, ReadingDay):model.__table__.create(connection,checkfirst=True)

if __name__=='__main__':
    with engine.begin() as connection:migrate(connection)
    print('Reading session migration complete.')
