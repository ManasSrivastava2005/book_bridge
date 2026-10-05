"""JWT-owned reader state. No caller-supplied owner IDs and no document fetching."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.digital_resource import DigitalResource
from app.models.reader_state import ReaderState
from app.schemas.reader import ReaderWrite, ReaderResponse
from app.services.ebook_storage import authorize

router = APIRouter(prefix='/reader', tags=['Reader'])


def check_resource(db, resource_id, user):
    resource = db.get(DigitalResource, resource_id)
    if not resource or (not resource.is_published and user.role.value not in ('librarian', 'admin')):
        raise HTTPException(404, 'Digital resource not found')
    authorize(resource, user)
    return resource


@router.get('/{resource_id}/state', response_model=ReaderResponse)
def get_reader_state(resource_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    check_resource(db, resource_id, user)
    row = db.query(ReaderState).filter_by(user_id=user.id, resource_id=resource_id).first()
    return {**row.data, 'version': row.version} if row else ReaderResponse()


@router.put('/{resource_id}/state', response_model=ReaderResponse)
def save_reader_state(resource_id: int, payload: ReaderWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    check_resource(db, resource_id, user)
    data = payload.model_dump(exclude={'version'})
    if payload.version == 0:
        db.add(ReaderState(user_id=user.id, resource_id=resource_id, version=1, data=data))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Reading data changed in another session. Reload before saving again.') from None
    else:
        result = db.execute(update(ReaderState).where(
            ReaderState.user_id == user.id, ReaderState.resource_id == resource_id,
            ReaderState.version == payload.version,
        ).values(data=data, version=payload.version+1))
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(409, 'Reading data changed in another session. Reload before saving again.')
        db.commit()
    return {**data, 'version': payload.version+1}
