from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import engine
from app.services.badges import seed_badges

def migrate(connection):
    connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_user_badge ON user_badges (user_id,badge_id)'))
    with Session(bind=connection) as db:
        seed_badges(db);db.flush()

if __name__=='__main__':
    with engine.begin() as connection:migrate(connection)
    print('Badge definitions and ownership uniqueness verified.')
