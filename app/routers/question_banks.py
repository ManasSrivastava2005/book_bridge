from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.question_bank import QuestionBank
from app.models.user import User
from app.schemas.question_bank import QuestionBankCreate, QuestionBankResponse

router = APIRouter(prefix="/question-banks", tags=["Question Banks"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "question_banks")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", response_model=List[QuestionBankResponse])
def get_question_banks(
    subject: Optional[str] = None,
    semester: Optional[int] = None,
    branch: Optional[str] = None,
    exam_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    search: Optional[str] = None,
    library_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    List question banks with filters for subject, semester, branch, exam type.
    """
    query = db.query(QuestionBank)

    if subject and subject != "all":
        query = query.filter(QuestionBank.subject.ilike(f"%{subject}%"))
    if semester:
        query = query.filter(QuestionBank.semester == semester)
    if branch and branch != "all":
        query = query.filter(QuestionBank.branch.ilike(f"%{branch}%"))
    if exam_type and exam_type != "all":
        query = query.filter(QuestionBank.exam_type.ilike(f"%{exam_type}%"))
    if academic_year:
        query = query.filter(QuestionBank.academic_year == academic_year)
    if library_id:
        query = query.filter(QuestionBank.library_id == library_id)
    if search:
        query = query.filter(
            QuestionBank.title.ilike(f"%{search}%")
            | QuestionBank.description.ilike(f"%{search}%")
            | QuestionBank.subject.ilike(f"%{search}%")
        )

    return query.order_by(QuestionBank.created_at.desc()).all()


@router.get("/{qb_id}", response_model=QuestionBankResponse)
def get_question_bank(qb_id: int, db: Session = Depends(get_db)):
    qb = db.query(QuestionBank).filter(QuestionBank.id == qb_id).first()
    if not qb:
        raise HTTPException(status_code=404, detail="Question bank not found")
    return qb


@router.post("/", response_model=QuestionBankResponse, status_code=201)
def create_question_bank(
    qb_data: QuestionBankCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("librarian", "admin")),
):
    """Upload or register exam question bank (librarian/admin only)."""
    new_qb = QuestionBank(
        **qb_data.model_dump(),
        user_id=current_user.id,
    )
    db.add(new_qb)
    db.commit()
    db.refresh(new_qb)
    return new_qb


@router.delete("/{qb_id}", status_code=204)
def delete_question_bank(
    qb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("librarian", "admin")),
):
    qb = db.query(QuestionBank).filter(QuestionBank.id == qb_id).first()
    if not qb:
        raise HTTPException(status_code=404, detail="Question bank not found")
    db.delete(qb)
    from sqlalchemy.exc import IntegrityError
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This question resource is referenced by a curriculum or contribution history and cannot be deleted.") from exc
    return None


@router.post('/{qb_id}/download')
def record_download(qb_id:int,db:Session=Depends(get_db)):
    from sqlalchemy import update,func
    from app.models.resource_usage import ResourceUsage
    row=db.execute(update(QuestionBank).where(QuestionBank.id==qb_id,QuestionBank.file_url.isnot(None)).values(download_count=func.coalesce(QuestionBank.download_count,0)+1).returning(QuestionBank.title,QuestionBank.download_count)).first()
    if not row:raise HTTPException(404,'Question resource file not found')
    db.add(ResourceUsage(resource_kind='question_bank',resource_id=qb_id,title=row.title));db.commit()
    return {'download_count':row.download_count}
