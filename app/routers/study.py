"""Authenticated rooms with explicit membership, bounded history and retry-safe posts."""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import func
from datetime import timedelta,datetime,timezone
import secrets
import uuid
import logging
from pathlib import Path
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from app.models.notification import Notification
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.study import StudyRoom, StudyMember, StudyMessage, StudyAudit, StudyReport, StudyAttachment
from app.schemas.study import RoomCreate, RoomArchive, MessageCreate, ReportCreate, RoomEdit, MessageEdit

router = APIRouter(prefix='/study', tags=['Study Together'])


ATTACHMENT_DIR = Path(__file__).resolve().parents[2] / 'private_uploads' / 'study'


def audit(db, room_id, user_id, action, detail=''):
    db.add(StudyAudit(room_id=room_id, actor_id=user_id, action=action, detail=detail))


def rate_limit(db, user, action, maximum, seconds):
    # NO KEY UPDATE serializes this account without blocking notification FK reads
    # by another member posting in the same room.
    db.query(User).filter(User.id == user.id).with_for_update(key_share=True).first()
    now = db.query(func.current_timestamp()).scalar().replace(tzinfo=None)
    count = db.query(func.count()).select_from(StudyAudit).filter(
        StudyAudit.actor_id == user.id, StudyAudit.action == action,
        StudyAudit.created_at >= now - timedelta(seconds=seconds),
    ).scalar()
    if count >= maximum:
        raise HTTPException(429, 'Too many requests. Please wait before trying again.', headers={'Retry-After': str(seconds)})


def invite_access(db, room, user, invite=None):
    if room.is_private and not member(db, room.id, user.id) and not moderator(room, user):
        if not invite or not room.invite_code or not secrets.compare_digest(invite, room.invite_code):
            raise HTTPException(404, 'Study room not found')


def discussion_access(db, room, user):
    if not member(db, room.id, user.id) and not moderator(room, user):
        raise HTTPException(403, 'Join this room to access its discussion and files.')


def room_or_404(db, room_id, lock=False):
    query = db.query(StudyRoom).filter(StudyRoom.id == room_id)
    room = (query.with_for_update() if lock else query).first()
    if not room:
        raise HTTPException(404, 'Study room not found')
    return room


def member(db, room_id, user_id):
    row=db.get(StudyMember,(room_id,user_id))
    return row is not None and row.left_at is None


def room_data(db, room, user):
    return {'id': room.id, 'owner_id': room.owner_id, 'title': room.title, 'subject': room.subject,
            'description': room.description, 'archived': room.archived, 'created_at': room.created_at,
            'is_private': room.is_private, 'invite_code': room.invite_code if room.owner_id == user.id else None,
            'is_member': member(db, room.id, user.id),
            'member_count': db.query(func.count()).select_from(StudyMember).filter(StudyMember.room_id == room.id,StudyMember.left_at.is_(None)).scalar()}


def moderator(room, user):
    return room.owner_id == user.id or user.role.value in ('admin', 'librarian')


@router.get('/rooms')
def rooms(search: str = Query('', max_length=120), mine: bool = False,
          before: int | None = Query(None, gt=0), limit: int = Query(20, ge=1, le=50),
          db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    membership = db.query(StudyMember.room_id).filter(StudyMember.user_id == user.id,StudyMember.left_at.is_(None))
    query = db.query(StudyRoom)
    if mine:
        query = query.filter(StudyRoom.id.in_(membership))
    else:
        query = query.filter(StudyRoom.archived == False, (StudyRoom.is_private == False) | StudyRoom.id.in_(membership))
    if search.strip():
        term = '%' + search.strip() + '%'
        query = query.filter(StudyRoom.title.ilike(term) | StudyRoom.subject.ilike(term))
    if before:
        query = query.filter(StudyRoom.id < before)
    rows = query.order_by(StudyRoom.id.desc()).limit(limit + 1).all()
    page = rows[:limit]
    ids = [r.id for r in page]
    counts = dict(db.query(StudyMember.room_id, func.count()).filter(StudyMember.room_id.in_(ids),StudyMember.left_at.is_(None)).group_by(StudyMember.room_id).all())
    joined = {r[0] for r in membership.filter(StudyMember.room_id.in_(ids)).all()}
    return {'items': [{'id': r.id, 'owner_id': r.owner_id, 'title': r.title, 'subject': r.subject,
                      'description': r.description, 'archived': r.archived, 'created_at': r.created_at, 'is_private': r.is_private,
                      'member_count': counts.get(r.id, 0), 'is_member': r.id in joined} for r in page],
            'next_before': page[-1].id if len(rows) > limit else None}


@router.post('/rooms', status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rate_limit(db, user, 'create_room', 5, 3600)
    room = StudyRoom(**payload.model_dump(), owner_id=user.id, invite_code=secrets.token_urlsafe(32) if payload.is_private else None)
    db.add(room)
    db.flush()
    db.add(StudyMember(room_id=room.id,user_id=user.id,role='OWNER'))
    audit(db, room.id, user.id, 'create_room')
    db.commit()
    db.refresh(room)
    return room_data(db, room, user)


@router.get('/rooms/{room_id}')
def get_room(room_id: int, invite: str | None = Query(None, max_length=64), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id)
    invite_access(db, room, user, invite)
    return room_data(db, room, user)


@router.post('/rooms/{room_id}/join')
def join_room(room_id: int, invite: str | None = Query(None, max_length=64), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id, lock=True)
    invite_access(db, room, user, invite)
    if room.archived:
        raise HTTPException(409, 'This room is archived. New members cannot join.')
    if not member(db, room_id, user.id):
        if db.query(func.count()).select_from(StudyMember).filter(StudyMember.room_id == room_id,StudyMember.left_at.is_(None)).scalar() >= 100:
            raise HTTPException(409, 'This study room has reached its 100-member limit.')
        previous=db.get(StudyMember,(room_id,user.id))
        if previous:previous.left_at=None;previous.last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
        else:db.add(StudyMember(room_id=room_id,user_id=user.id))
        audit(db, room_id, user.id, 'join_room')
    db.commit()
    return room_data(db, room, user)


@router.post('/rooms/{room_id}/leave', status_code=204)
def leave_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id, lock=True)
    if room.owner_id == user.id:
        raise HTTPException(409, 'The owner must remain in the room. You can archive it instead.')
    if member(db, room_id, user.id):
        audit(db, room_id, user.id, 'leave_room')
    membership=db.get(StudyMember,(room_id,user.id))
    if membership and membership.left_at is None:membership.left_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


@router.patch('/rooms/{room_id}')
def archive_room(room_id: int, payload: RoomArchive, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id, lock=True)
    if not moderator(room, user):
        raise HTTPException(403, 'Only the room owner or library staff can archive or reopen a room.')
    audit(db, room_id, user.id, 'archive_room' if payload.archived else 'reopen_room')
    room.archived = payload.archived
    db.commit()
    return room_data(db, room, user)


@router.get('/rooms/{room_id}/messages')
def messages(room_id: int, before: int | None = Query(None, gt=0), limit: int = Query(50, ge=1, le=100),
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id)
    if not member(db, room_id, user.id) and not moderator(room, user):
        raise HTTPException(403, 'Join this room to read its discussion.')
    query = db.query(StudyMessage, User.name).join(User, User.id == StudyMessage.user_id).filter(StudyMessage.room_id == room_id)
    if before:
        query = query.filter(StudyMessage.id < before)
    rows = query.order_by(StudyMessage.id.desc()).limit(limit + 1).all()
    page = rows[:limit]
    return {'items':[message_data(db,m,user,room,name) for m,name in reversed(page)],'next_before':page[-1][0].id if len(rows)>limit else None}



@router.post('/rooms/{room_id}/messages', status_code=201)
def post_message(room_id: int, payload: MessageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    duplicate = db.query(StudyMessage).filter_by(room_id=room_id, user_id=user.id, client_id=str(payload.client_id)).first()
    if not duplicate:
        rate_limit(db, user, 'post_message', 20, 60)
    # Same room lock serializes join, leave, archive, post and moderation writes.
    room = room_or_404(db, room_id, lock=True)
    if not member(db, room_id, user.id):
        raise HTTPException(403, 'Join this room before posting.')
    existing = db.query(StudyMessage).filter(StudyMessage.room_id == room_id, StudyMessage.user_id == user.id,
                                            StudyMessage.client_id == str(payload.client_id)).first()
    if existing:
        if existing.body != payload.body or existing.reply_to_id != payload.reply_to_id:
            raise HTTPException(409, 'This message request was already used for different text.')
        return {'id': existing.id}
    if room.archived:
        raise HTTPException(409, 'This room is archived and its discussion is read-only.')
    if payload.reply_to_id:
        parent=db.get(StudyMessage,payload.reply_to_id)
        if not parent or parent.room_id!=room_id:raise HTTPException(422,'Reply must reference a message in this room.')
    message = StudyMessage(room_id=room_id,user_id=user.id,body=payload.body,client_id=str(payload.client_id),reply_to_id=payload.reply_to_id)
    db.add(message)
    db.flush()
    audit(db, room_id, user.id, 'post_message', str(message.id))
    recipients = db.query(StudyMember.user_id).filter(StudyMember.room_id == room_id, StudyMember.user_id != user.id,StudyMember.left_at.is_(None)).all()
    for (recipient,) in recipients:
        db.add(Notification(user_id=recipient, message=f'New discussion in Study Together: {room.title}', is_read=False))
    db.commit()
    db.refresh(message)
    return {'id': message.id}


@router.delete('/rooms/{room_id}/messages/{message_id}', status_code=204)
def delete_message(room_id: int, message_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id, lock=True)
    message = db.query(StudyMessage).filter(StudyMessage.id == message_id, StudyMessage.room_id == room_id).first()
    if not message:
        raise HTTPException(404, 'Message not found')
    if message.user_id != user.id and not moderator(room, user):
        raise HTTPException(403, 'You cannot remove this message.')
    if message.deleted_at:return
    audit(db,room_id,user.id,'remove_message',f'Message {message.id} by account {message.user_id}: {message.body}')
    message.deleted_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


@router.post('/rooms/{room_id}/messages/{message_id}/report', status_code=201)
def report_message(room_id: int, message_id: int, payload: ReportCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rate_limit(db, user, 'report_message', 10, 3600)
    room = room_or_404(db, room_id, lock=True)
    discussion_access(db, room, user)
    message = db.query(StudyMessage).filter(StudyMessage.id == message_id, StudyMessage.room_id == room_id).first()
    if not message:
        raise HTTPException(404, 'Message not found')
    report = db.query(StudyReport).filter_by(message_id=message_id, reporter_id=user.id).first()
    if not report:
        report = StudyReport(room_id=room_id, message_id=message_id, reporter_id=user.id, reason=payload.reason)
        db.add(report)
        audit(db, room_id, user.id, 'report_message', str(message_id))
    db.commit()
    return {'status': 'reported'}


def staff_only(user):
    if user.role.value not in ('admin', 'librarian'):
        raise HTTPException(403, 'Library staff only')


@router.get('/reports')
def reports(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staff_only(user)
    rows = db.query(StudyReport).filter(StudyReport.resolved == False).order_by(StudyReport.id).limit(100).all()
    return [{'id': row.id, 'room_id': row.room_id, 'message_id': row.message_id, 'reason': row.reason, 'created_at': row.created_at} for row in rows]


@router.post('/reports/{report_id}/resolve')
def resolve_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staff_only(user)
    row = db.get(StudyReport, report_id)
    if not row:
        raise HTTPException(404, 'Report not found')
    # Match moderation's room-before-report order to avoid lock inversions.
    room_or_404(db, row.room_id, lock=True)
    db.refresh(row, with_for_update=True)
    if not row.resolved:
        row.resolved = True
        audit(db, row.room_id, user.id, 'resolve_report', str(row.id))
    db.commit()
    return {'status': 'resolved'}


@router.get('/audit')
def audit_log(before: int | None = Query(None, gt=0), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    staff_only(user)
    query = db.query(StudyAudit)
    if before:
        query = query.filter(StudyAudit.id < before)
    rows = query.order_by(StudyAudit.id.desc()).limit(100).all()
    return [{'id': row.id, 'room_id': row.room_id, 'actor_id': row.actor_id, 'action': row.action,
             'detail': row.detail, 'created_at': row.created_at} for row in rows]


@router.get('/rooms/{room_id}/attachments')
def attachments(room_id: int, before: int | None = Query(None, gt=0), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id)
    discussion_access(db, room, user)
    query = db.query(StudyAttachment).filter(StudyAttachment.room_id == room_id)
    if before:
        query = query.filter(StudyAttachment.id < before)
    rows = query.order_by(StudyAttachment.id.desc()).limit(50).all()
    return [{'id': row.id, 'filename': row.filename, 'size': row.size, 'can_delete': row.user_id == user.id or moderator(room, user)} for row in rows]


@router.post('/rooms/{room_id}/attachments', status_code=201)
async def upload_attachment(room_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rate_limit(db, user, 'upload_attachment', 5, 60)
    room = room_or_404(db, room_id, lock=True)
    if not member(db, room_id, user.id):
        raise HTTPException(403, 'Join the room before uploading.')
    if room.archived:
        raise HTTPException(409, 'Archived rooms cannot accept files.')
    name = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
    extension = Path(name).suffix.lower()
    if extension not in ('.pdf', '.txt') or not name or len(name) > 180 or any(ord(c) < 32 for c in name):
        raise HTTPException(400, 'Choose a PDF or TXT file with a name up to 180 characters.')
    contents = await file.read(10 * 1024 * 1024 + 1)
    if not contents or len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, 'Choose a non-empty file up to 10 MB.')
    if extension == '.pdf' and not contents.startswith(b'%PDF-'):
        raise HTTPException(400, 'Invalid PDF document.')
    if extension == '.txt':
        try:
            contents.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(400, 'Text files must use UTF-8.') from None
    filename = uuid.uuid4().hex + extension
    path = ATTACHMENT_DIR / filename
    created = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            created = True
            stream.write(contents)
        item = StudyAttachment(room_id=room_id, user_id=user.id, filename=name, storage_name=filename, size=len(contents))
        db.add(item)
        db.flush()
        audit(db, room_id, user.id, 'upload_attachment', str(item.id))
        db.commit()
        return {'id': item.id}
    except (OSError, SQLAlchemyError):
        db.rollback()
        if created:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logging.getLogger(__name__).error('Failed to clean up room attachment')
        raise HTTPException(500, 'Unable to save the attachment.') from None


@router.get('/rooms/{room_id}/attachments/{attachment_id}')
def download_attachment(room_id: int, attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id)
    discussion_access(db, room, user)
    item = db.query(StudyAttachment).filter_by(id=attachment_id, room_id=room_id).first()
    if not item or not (ATTACHMENT_DIR / item.storage_name).is_file():
        raise HTTPException(404, 'Attachment not found')
    return FileResponse(ATTACHMENT_DIR / item.storage_name, filename=item.filename,
                        media_type='application/octet-stream', headers={'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'})


@router.delete('/rooms/{room_id}/attachments/{attachment_id}', status_code=204)
def delete_attachment(room_id: int, attachment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = room_or_404(db, room_id, lock=True)
    item = db.query(StudyAttachment).filter_by(id=attachment_id, room_id=room_id).first()
    if not item:
        raise HTTPException(404, 'Attachment not found')
    if item.user_id != user.id and not moderator(room, user):
        raise HTTPException(403, 'You cannot remove this attachment.')
    path = ATTACHMENT_DIR / item.storage_name
    audit(db, room_id, user.id, 'remove_attachment', str(item.id))
    db.delete(item)
    db.commit()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logging.getLogger(__name__).error('Failed to remove room attachment file')


def message_data(db,message,user,room,author=None):
    reply=db.get(StudyMessage,message.reply_to_id) if message.reply_to_id else None
    return {'id':message.id,'user_id':message.user_id,'author':author or db.get(User,message.user_id).name,
            'body':'This message was deleted' if message.deleted_at else message.body,'created_at':message.created_at,
            'edited_at':message.edited_at,'deleted_at':message.deleted_at,'reply_to_id':message.reply_to_id,
            'reply':{'id':reply.id,'author':db.get(User,reply.user_id).name,'body':'This message was deleted' if reply.deleted_at else reply.body[:240]} if reply else None,
            'can_edit':not message.deleted_at and not room.archived and message.user_id==user.id and member(db,room.id,user.id),
            'can_delete':not message.deleted_at and (message.user_id==user.id or moderator(room,user))}

@router.patch('/rooms/{room_id}/details')
def edit_room(room_id:int,payload:RoomEdit,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    room=room_or_404(db,room_id,lock=True)
    if not moderator(room,user):raise HTTPException(403,'Only the room owner or library staff can edit room details.')
    audit(db,room_id,user.id,'edit_room',room.title)
    for key,value in payload.model_dump().items():setattr(room,key,value)
    db.commit();return room_data(db,room,user)

@router.patch('/rooms/{room_id}/messages/{message_id}')
def edit_message(room_id:int,message_id:int,payload:MessageEdit,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    room=room_or_404(db,room_id,lock=True)
    message=db.query(StudyMessage).filter_by(id=message_id,room_id=room_id).first()
    if not message:raise HTTPException(404,'Message not found')
    if message.user_id!=user.id or not member(db,room_id,user.id):raise HTTPException(403,'Only a joined sender may edit their own message.')
    if room.archived or message.deleted_at:raise HTTPException(409,'This message cannot be edited.')
    audit(db,room_id,user.id,'edit_message',f'{message.id}: {message.body}')
    message.body=payload.body;message.edited_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit();return message_data(db,message,user,room)

@router.get('/rooms/{room_id}/participants')
def participants(room_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    room=room_or_404(db,room_id);discussion_access(db,room,user)
    cutoff=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(minutes=3)
    rows=db.query(StudyMember,User.name).join(User,User.id==StudyMember.user_id).filter(StudyMember.room_id==room_id,StudyMember.left_at.is_(None)).order_by(StudyMember.joined_at).all()
    return {'activity_window_seconds':180,'items':[{'user_id':m.user_id,'name':name,'role':'OWNER' if m.user_id==room.owner_id else m.role,'joined_at':m.joined_at,'recently_active':bool(m.last_seen_at and m.last_seen_at>=cutoff)} for m,name in rows]}

@router.post('/rooms/{room_id}/presence',status_code=204)
def presence(room_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    room=room_or_404(db,room_id,lock=True)
    if not member(db,room_id,user.id):raise HTTPException(403,'Join this room first.')
    db.get(StudyMember,(room_id,user.id)).last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None);db.commit()

@router.get('/dashboard/rooms')
def dashboard_rooms(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    rows=db.query(StudyRoom,StudyMember).join(StudyMember,StudyMember.room_id==StudyRoom.id).filter(StudyMember.user_id==user.id,StudyMember.left_at.is_(None),StudyRoom.archived.is_(False)).order_by(StudyRoom.created_at.desc()).all()
    items=[]
    for room,membership in rows[:5]:
        messages=db.query(StudyMessage).filter(StudyMessage.room_id==room.id,StudyMessage.deleted_at.is_(None))
        latest=messages.order_by(StudyMessage.id.desc()).first()
        unseen=messages.filter(StudyMessage.user_id!=user.id,StudyMessage.created_at>(membership.last_seen_at or membership.joined_at)).count()
        items.append({'id':room.id,'title':room.title,'new_messages':unseen,'latest_activity':latest.created_at if latest else room.created_at})
    return {'joined_count':len(rows),'items':items}
