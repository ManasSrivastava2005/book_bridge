"""Backend-only XP events. Callers own the transaction; clients cannot set rewards."""
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models.contribution import XPTransaction
from app.models.user import UserRole

# Calendar-day rewards use UTC consistently, independent of client clocks.
DAILY_LOGIN_XP = 25

def award_login(db, user, now=None):
    if user.role != UserRole.STUDENT:
        return False
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Reward time must include a timezone')
    day = now.astimezone(timezone.utc).date().isoformat()
    values = dict(user_id=user.id, amount=DAILY_LOGIN_XP, event_type='LOGIN',
                  event_key=f'LOGIN:{user.id}:{day}', description='Daily login',
                  created_at=now.astimezone(timezone.utc).replace(tzinfo=None))
    dialect = db.get_bind().dialect.name
    insert = pg_insert if dialect == 'postgresql' else sqlite_insert if dialect == 'sqlite' else None
    if insert is None:
        raise RuntimeError('Unsupported XP database dialect')
    result = db.execute(insert(XPTransaction).values(**values).on_conflict_do_nothing(index_elements=['event_key']))
    return result.rowcount == 1

def level_from_xp(lifetime_xp):
    lifetime_xp = max(0, int(lifetime_xp))
    level = 1
    remaining = lifetime_xp
    while level < 50 and remaining >= 200 * level:
        remaining -= 200 * level
        level += 1
    required = 200 * level
    current = min(remaining, required)
    title = next(title for threshold, title in (
        (50, 'Book Bridge Legend'), (35, 'Knowledge Master'), (20, 'Gold Scholar'),
        (10, 'Silver Scholar'), (5, 'Bronze Reader'), (1, 'New Reader')) if level >= threshold)
    return dict(level=level, level_title=title, lifetime_xp=lifetime_xp,
                current_level_xp=current, xp_required_this_level=required,
                xp_remaining=required-current, progress_percent=round(current/required*100, 2))

def reader_level(db, user_id):
    from sqlalchemy import func
    lifetime = db.query(func.coalesce(func.sum(XPTransaction.amount), 0)).filter(XPTransaction.user_id == user_id).scalar()
    return level_from_xp(lifetime)
