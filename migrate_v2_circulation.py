"""Add staff checkout metadata and retain reservation fulfillment history."""
from sqlalchemy import inspect, text

def migrate(c):
    columns={x['name'] for x in inspect(c).get_columns('borrow_records')}
    for name,definition in [('issued_by','INTEGER REFERENCES users(id)'),('request_key','VARCHAR(36)'),('request_hash','VARCHAR(64)')]:
        if name not in columns:c.execute(text(f'ALTER TABLE borrow_records ADD COLUMN {name} {definition}'))
    c.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_loan_request_key ON borrow_records (request_key)'))
    columns={x['name'] for x in inspect(c).get_columns('reservations')}
    for name,definition in [('loan_id','INTEGER REFERENCES borrow_records(id)'),('ready_at','TIMESTAMP'),('fulfilled_at','TIMESTAMP'),('cancelled_at','TIMESTAMP')]:
        if name not in columns:c.execute(text(f'ALTER TABLE reservations ADD COLUMN {name} {definition}'))
    # Legacy fulfilled means held. New fulfilled records always reference the loan.
    c.execute(text("UPDATE reservations SET status='ready' WHERE status='fulfilled' AND loan_id IS NULL"))

if __name__=='__main__':
    from app.database import engine
    with engine.begin() as c:migrate(c)
    print('Circulation migration complete.')
