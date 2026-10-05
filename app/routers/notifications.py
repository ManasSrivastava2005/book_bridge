from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.services.overdue_reminders import remind_overdue
from app.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=list[NotificationResponse])
def get_notifications(limit: int = Query(100, ge=1, le=100), before: int | None = Query(None, gt=0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    remind_overdue(db, current_user.id)
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if before:
        query = query.filter(Notification.id < before)
    return query.order_by(Notification.id.desc()).limit(limit).all()


@router.get('/unread-count')
def unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    remind_overdue(db, current_user.id)
    return {'count': db.query(func.count(Notification.id)).filter(Notification.user_id == current_user.id, Notification.is_read == False).scalar()}


@router.put('/read-all')
def read_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({'is_read': True})
    db.commit()
    return {'status': 'ok'}

@router.put("/{notif_id}/read", response_model=NotificationResponse)
def mark_read(notif_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(404, 'Notification not found')
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif
