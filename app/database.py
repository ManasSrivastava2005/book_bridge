from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

# --- THE ENGINE ---
# The engine is the starting point for any SQLAlchemy application.
# Think of it as the "connection manager" to your PostgreSQL database.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# --- THE SESSION ---
# A session is like a "conversation" with the database.
# Every time an API request needs to read/write data, it opens a session,
# does its work, and then closes it.
SessionLocal = sessionmaker(bind=engine)


# --- THE BASE CLASS ---
# All our database models (tables) will inherit from this class.
# SQLAlchemy uses this to keep track of all tables.
class Base(DeclarativeBase):
    pass


def get_db():
    """
    Dependency function that provides a database session to API endpoints.

    How it works:
    1. Creates a new session (opens a conversation with the DB)
    2. Gives it to the endpoint via 'yield'
    3. After the endpoint finishes, closes the session (cleanup)

    The 'finally' block ensures the session is ALWAYS closed,
    even if an error occurs. This prevents connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
