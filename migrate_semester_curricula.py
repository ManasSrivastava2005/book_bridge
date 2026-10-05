"""Expand owner uniqueness to owner+semester without deleting or moving any data."""
from sqlalchemy import inspect,text

def migrate(c):
    inspector=inspect(c)
    # Existing single-owner uniqueness must be replaced to allow retained semesters.
    # All unrelated constraints remain untouched.
    for item in inspector.get_unique_constraints('curricula'):
        if item['column_names']==['owner_user_id']:
            name=c.dialect.identifier_preparer.quote(item['name'])
            c.execute(text('ALTER TABLE curricula DROP CONSTRAINT '+name))
    for item in inspect(c).get_indexes('curricula'):
        if item.get('unique') and item['column_names']==['owner_user_id']:
            c.execute(text('DROP INDEX '+c.dialect.identifier_preparer.quote(item['name'])))
    c.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_personal_curriculum_semester ON curricula(owner_user_id,semester)'))
