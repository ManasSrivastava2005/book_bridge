from sqlalchemy import inspect,text
from app.database import engine

def migrate(connection):
    columns={c['name'] for c in inspect(connection).get_columns('contributions')}
    for name,size in [('request_key',36),('payload_hash',64)]:
        if name not in columns:connection.execute(text(f'ALTER TABLE contributions ADD COLUMN {name} VARCHAR({size})'))
    connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_contribution_request ON contributions (user_id,request_key)'))
if __name__=='__main__':
    with engine.begin() as connection:migrate(connection)
    print('Contribution request deduplication migration complete.')
