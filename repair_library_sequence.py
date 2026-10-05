"""Inspect or advance only the libraries ID sequence; never renumber/delete rows."""
import argparse
from sqlalchemy import text
from app.database import engine


def repair(apply=False):
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('This maintenance operation requires PostgreSQL.')
    with engine.begin() as connection:
        connection.execute(text('LOCK TABLE libraries IN SHARE ROW EXCLUSIVE MODE'))
        sequence=connection.execute(text("SELECT pg_get_serial_sequence('libraries','id')")).scalar_one()
        if not sequence: raise RuntimeError('No library ID sequence found.')
        # PostgreSQL supplies the identifier; quote each component before reading it.
        qualified='.'.join(connection.dialect.identifier_preparer.quote(part) for part in sequence.split('.'))
        last,called=connection.execute(text('SELECT last_value,is_called FROM '+qualified)).one()
        highest,count=connection.execute(text('SELECT coalesce(max(id),0),count(*) FROM libraries')).one()
        next_id=last+1 if called else last
        changed=False
        if apply and next_id<=highest:
            connection.execute(text('SELECT setval(CAST(:sequence AS regclass),:value,true)'),{'sequence':sequence,'value':max(highest,last)})
            changed=True
        assert connection.execute(text('SELECT count(*) FROM libraries')).scalar_one()==count
        return {'sequence':sequence,'highest_existing_id':highest,'next_before':next_id,
                'repair_needed':next_id<=highest,'repaired':changed,'rows_unchanged':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true')
    print(repair(parser.parse_args().apply))
