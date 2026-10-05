"""Add only the reader_states table. Existing rows/tables are not modified."""
from app.database import engine
from app.models.user import User
from app.models.library import Library
from app.models.digital_resource import DigitalResource
from app.models.reader_state import ReaderState

if __name__ == '__main__':
    ReaderState.__table__.create(bind=engine, checkfirst=True)
    print('reader_states table is ready; existing records were preserved.')
