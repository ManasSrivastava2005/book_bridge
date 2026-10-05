from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.dependencies import require_role
from app.models.quiz import Quiz, QuizQuestion
from app.models.book import Book
from app.models.curriculum import Curriculum, CurriculumNode
from app.models.user import User

router=APIRouter(prefix='/admin/quizzes',tags=['Staff quizzes'],dependencies=[Depends(require_role('librarian','admin'))])

class QuestionWrite(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    prompt:str=Field(min_length=1,max_length=3000)
    options:list[str]=Field(min_length=2,max_length=6)
    correct_index:int=Field(ge=0)
    explanation:str=Field(min_length=1,max_length=3000)
    @model_validator(mode='after')
    def validate_answers(self):
        self.options=[x.strip() for x in self.options]
        if any(not x or len(x)>1000 for x in self.options) or len(set(self.options))!=len(self.options):raise ValueError('Options must be nonempty and distinct')
        if self.correct_index>=len(self.options):raise ValueError('Correct answer must refer to an option')
        return self

class QuizWrite(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    title:str=Field(min_length=1,max_length=200)
    subject_id:int|None=Field(None,gt=0)
    topic_id:int|None=Field(None,gt=0)
    book_id:int|None=Field(None,gt=0)
    chapter:str|None=Field(None,max_length=200)
    source_kind:Literal['librarian_original','permitted_material']='librarian_original'
    source_reference:str|None=Field(None,max_length=1000)
    permission_confirmed:bool=False
    questions:list[QuestionWrite]=Field(default_factory=list,max_length=10)

class StateWrite(BaseModel):
    status:Literal['draft','published']
    active:bool=False

def mappings(payload,db):
    if payload.book_id and not db.get(Book,payload.book_id):raise HTTPException(404,'Book not found')
    subject=db.get(CurriculumNode,payload.subject_id) if payload.subject_id else None
    if payload.subject_id and (not subject or subject.kind!='subject' or db.get(Curriculum,subject.curriculum_id).owner_user_id is not None):raise HTTPException(422,'Invalid subject')
    if payload.topic_id:
        topic=db.get(CurriculumNode,payload.topic_id)
        if not topic or topic.kind!='topic' or db.get(Curriculum,topic.curriculum_id).owner_user_id is not None:raise HTTPException(422,'Invalid topic')
        unit=db.get(CurriculumNode,topic.parent_id);parent=db.get(CurriculumNode,unit.parent_id)
        if subject and parent.id!=subject.id:raise HTTPException(422,'Topic does not belong to selected subject')
        payload.subject_id=parent.id

def get_quiz(db,id):
    row=db.query(Quiz).filter_by(id=id).with_for_update().first()
    if not row:raise HTTPException(404,'Quiz not found')
    return row

def write_questions(db,id,questions):
    db.query(QuizQuestion).filter_by(quiz_id=id).delete();db.flush()
    for i,q in enumerate(questions):db.add(QuizQuestion(quiz_id=id,position=i,**q.model_dump()))

@router.get('')
def listing(db:Session=Depends(get_db)):
    return db.query(Quiz).order_by(Quiz.id.desc()).all()

@router.get('/{id}')
def detail(id:int,db:Session=Depends(get_db)):
    return {'quiz':get_quiz(db,id),'questions':db.query(QuizQuestion).filter_by(quiz_id=id).order_by(QuizQuestion.position).all()}

@router.post('',status_code=201)
def create(payload:QuizWrite,db:Session=Depends(get_db),staff:User=Depends(require_role('librarian','admin'))):
    mappings(payload,db);row=Quiz(**payload.model_dump(exclude={'questions'}),created_by=staff.id,status='draft',active=False)
    db.add(row);db.flush();write_questions(db,row.id,payload.questions);db.commit();db.refresh(row);return row

@router.put('/{id}')
def edit(id:int,payload:QuizWrite,db:Session=Depends(get_db)):
    row=get_quiz(db,id)
    if row.status!='draft':raise HTTPException(409,'Move this quiz to draft before editing')
    mappings(payload,db)
    for k,v in payload.model_dump(exclude={'questions'}).items():setattr(row,k,v)
    write_questions(db,id,payload.questions);db.commit();db.refresh(row);return row

@router.patch('/{id}/state')
def state(id:int,payload:StateWrite,db:Session=Depends(get_db)):
    row=get_quiz(db,id)
    if payload.status=='published':
        if db.query(QuizQuestion).filter_by(quiz_id=id).count()!=10:raise HTTPException(422,'A published quiz must contain exactly 10 questions')
        if not row.permission_confirmed:raise HTTPException(422,'Confirm permission to use the question material')
        if row.source_kind=='permitted_material' and not row.source_reference:raise HTTPException(422,'Record the permitted source reference')
        if not (row.subject_id or (row.book_id and row.chapter)):raise HTTPException(422,'Map the quiz to a subject or book chapter')
        if row.subject_id:
            node=db.get(CurriculumNode,row.subject_id)
            if db.get(Curriculum,node.curriculum_id).archived:raise HTTPException(409,'Cannot publish against an archived curriculum')
    row.status=payload.status;row.active=payload.active if payload.status=='published' else False
    db.commit();db.refresh(row);return row

@router.delete('/{id}',status_code=204)
def delete(id:int,db:Session=Depends(get_db)):
    row=get_quiz(db,id)
    if row.status!='draft':raise HTTPException(409,'Move this quiz to draft before deleting')
    db.query(QuizQuestion).filter_by(quiz_id=id).delete();db.delete(row)
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Quiz is referenced by learning history and must be retained')
