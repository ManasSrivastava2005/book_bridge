"""Student phase 1: additive metadata for the existing XP ledger."""
from sqlalchemy import inspect, text
from app.database import engine

def migrate(connection):
    columns = {column['name'] for column in inspect(connection).get_columns('xp_transactions')}
    if 'event_type' not in columns:
        connection.execute(text("ALTER TABLE xp_transactions ADD COLUMN event_type VARCHAR(30) NOT NULL DEFAULT 'CONTRIBUTION'"))
    if 'description' not in columns:
        connection.execute(text("ALTER TABLE xp_transactions ADD COLUMN description VARCHAR(255) NOT NULL DEFAULT 'Approved contribution'"))

if __name__ == '__main__':
    with engine.begin() as connection:
        migrate(connection)
    print('XP ledger metadata migration complete; existing rewards preserved.')
