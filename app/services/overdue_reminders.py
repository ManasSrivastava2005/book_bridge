from sqlalchemy import func
from app.models.borrow import BorrowRecord
from app.models.notification import Notification
from app.models.overdue_reminder import OverdueReminder


def remind_overdue(db,user_id):
    # Database-local timestamps match the legacy due_date columns.
    now=db.query(func.current_timestamp()).scalar().replace(tzinfo=None)
    loans=db.query(BorrowRecord).filter(BorrowRecord.user_id==user_id,BorrowRecord.status=='borrowed',BorrowRecord.due_date<now).order_by(BorrowRecord.id).with_for_update().all()
    for loan in loans:
        if not db.get(OverdueReminder,(loan.id,now.date())):
            notification=Notification(user_id=user_id,message=f'Overdue reminder: {loan.book.title} was due on {loan.due_date.date().isoformat()}. Please return it to your library.',is_read=False)
            db.add(notification);db.flush()
            db.add(OverdueReminder(borrow_id=loan.id,day=now.date(),notification_id=notification.id))
    db.commit()
