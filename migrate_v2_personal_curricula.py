"""Add private curriculum ownership and non-destructive node editing metadata."""
from sqlalchemy import inspect,text
def migrate(c):
    cols={x['name'] for x in inspect(c).get_columns('curricula')}
    if 'owner_user_id' not in cols:c.execute(text('ALTER TABLE curricula ADD COLUMN owner_user_id INTEGER REFERENCES users(id)'))
    c.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_personal_curriculum_owner ON curricula (owner_user_id)'))
    cols={x['name'] for x in inspect(c).get_columns('curriculum_nodes')}
    for name,definition in [('objectives','TEXT'),('subtopics','JSON'),('archived','BOOLEAN NOT NULL DEFAULT FALSE')]:
        if name not in cols:c.execute(text(f'ALTER TABLE curriculum_nodes ADD COLUMN {name} {definition}'))
