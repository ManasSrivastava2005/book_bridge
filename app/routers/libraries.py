from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import require_role, get_current_user
from app.models.library import Library
from app.models.book import Book
from app.schemas.library import LibraryCreate, LibraryResponse

router = APIRouter(prefix="/libraries", tags=["Libraries"])

@router.get("/", response_model=List[LibraryResponse])
def get_all_libraries(db: Session = Depends(get_db)):
    """List all active partner college libraries."""
    return db.query(Library).filter(Library.is_active == True).all()

@router.get("/{library_id}", response_model=LibraryResponse)
def get_library(library_id: int, db: Session = Depends(get_db)):
    """Get single library details."""
    library = db.query(Library).filter(Library.id == library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    return library

@router.post("/", response_model=LibraryResponse, status_code=201, dependencies=[Depends(require_role("librarian", "admin"))])
def create_library(library_data: LibraryCreate, db: Session = Depends(get_db)):
    """Create new partner library (librarian/admin only)."""
    existing = db.query(Library).filter(Library.code == library_data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Library code already exists")

    library = Library(**library_data.model_dump())
    db.add(library)
    db.commit()
    db.refresh(library)
    return library
