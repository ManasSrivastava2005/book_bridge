from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User,UserRole
from app.models.library import Library
from app.models.curriculum import SubjectEnrollment, CurriculumNode, Curriculum

router=APIRouter(prefix='/admin/users',tags=['Staff user management'],dependencies=[Depends(require_role('librarian','admin'))])
class MembershipWrite(BaseModel):
    library_id:int|None=Field(None,gt=0)

@router.put('/{id}/membership')
def membership(id:int,payload:MembershipWrite,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.id==id,User.role==UserRole.STUDENT).with_for_update().first()
    if not user:raise HTTPException(404,'Student not found')
    if payload.library_id is not None:
        library=db.get(Library,payload.library_id)
        if not library or not library.is_active:raise HTTPException(422,'Choose an active library')
    user.library_id=payload.library_id;db.commit();return {'user_id':id,'library_id':user.library_id}

@router.get('/{id}/subjects')
def subjects(id:int,db:Session=Depends(get_db)):
    return db.query(SubjectEnrollment).filter_by(user_id=id).all()

@router.delete('/{id}/subjects/{subject_id}',status_code=204)
def unenroll(id:int,subject_id:int,db:Session=Depends(get_db)):
    node=db.get(CurriculumNode,subject_id)
    if node and db.get(Curriculum,node.curriculum_id).owner_user_id is not None:raise HTTPException(403,'Personal subjects are managed by their student owner')
    db.query(SubjectEnrollment).filter_by(user_id=id,subject_id=subject_id).delete();db.commit()
