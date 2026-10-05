"""Add resource archiving without changing existing publication flags."""
from sqlalchemy import inspect, text

def migrate(connection):
    names={c['name'] for c in inspect(connection).get_columns('digital_resources')}
    if 'archived_at' not in names:
        connection.execute(text('ALTER TABLE digital_resources ADD COLUMN archived_at TIMESTAMP NULL'))

if __name__=='__main__':
    from app.database import engine
    with engine.begin() as c:migrate(c)
    print('Resource archive migration complete.')
