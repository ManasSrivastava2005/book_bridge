from fastapi import APIRouter,Depends,Query,Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.schemas.personal_curriculum import PersonalCurriculumWrite
from app.services.personal_curriculum import get_personal,save_personal,activate_semester

router=APIRouter(prefix='/academic/personal-curriculum',tags=['Personal curriculum'])
@router.get('')
def read(semester:int|None=Query(None,ge=1,le=20),db:Session=Depends(get_db),user:User=Depends(require_role('student'))):return get_personal(db,user,semester)

@router.put('')
def save(payload:PersonalCurriculumWrite,db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    save_personal(db,user,payload);db.commit();return get_personal(db,user)

@router.post('/semesters/{semester}/activate')
def activate(semester:int=Path(ge=1,le=20),db:Session=Depends(get_db),user:User=Depends(require_role('student'))):
    activate_semester(db,user,semester);db.commit();return get_personal(db,user)
