"""Add rights review metadata without approving or deleting legacy resources."""
from sqlalchemy import inspect,text

def migrate(c):
    columns={x['name'] for x in inspect(c).get_columns('digital_resources')}
    for name,definition in [('distribution_basis','VARCHAR(40)'),('rights_evidence','TEXT'),('reviewed_by','INTEGER REFERENCES users(id)'),('reviewed_at','TIMESTAMP')]:
        if name not in columns:c.execute(text(f'ALTER TABLE digital_resources ADD COLUMN {name} {definition}'))

if __name__=='__main__':
    from app.database import engine
    with engine.begin() as c:migrate(c)
    print('Curation columns added; existing resources remain unreviewed.')
