"""Authenticated, owner-scoped XP history; no client reward mutation routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.contribution import XPTransaction

router = APIRouter(prefix='/xp', tags=['XP'])

@router.get('/history')
def history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(XPTransaction).filter(XPTransaction.user_id == user.id)
    total = query.count()
    lifetime = db.query(func.coalesce(func.sum(XPTransaction.amount), 0)).filter(XPTransaction.user_id == user.id).scalar()
    rows = query.order_by(XPTransaction.created_at.desc(), XPTransaction.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {'lifetime_xp': lifetime, 'total': total, 'page': page, 'page_size': page_size,
            'calendar_timezone': 'UTC', 'items': [
                {'id': row.id, 'amount': row.amount, 'event_type': row.event_type,
                 'description': row.description, 'created_at': row.created_at.isoformat()+'Z'}
                for row in rows]}

@router.get('/level')
def level(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.xp import reader_level
    return reader_level(db, user.id)
