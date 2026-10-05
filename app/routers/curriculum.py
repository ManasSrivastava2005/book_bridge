from uuid import uuid4
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.dependencies import require_role
from app.models.curriculum import Curriculum, CurriculumNode, CurriculumResource, SubjectEnrollment
from app.models.book import Book
from app.models.digital_resource import DigitalResource
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.user import User, UserRole

router=APIRouter(prefix='/admin/curricula',tags=['Curriculum management'],dependencies=[Depends(require_role('librarian','admin'))])

class CurriculumWrite(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    title: str=Field(min_length=1,max_length=200)
    college: str=Field(min_length=1,max_length=200)
    program: str=Field(min_length=1,max_length=120)
    branch: str=Field(min_length=1,max_length=120)
    specialization: str|None=Field(None,max_length=120)
    semester: int=Field(ge=1,le=20)

class NodeWrite(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    title: str=Field(min_length=1,max_length=200)
    code: str|None=Field(None,max_length=50)
    position: int=Field(0,ge=0,le=10000)

class NodeCreate(NodeWrite):
    kind: Literal['subject','unit','topic']
    parent_id: int|None=None

class MappingWrite(BaseModel):
    kind: Literal['book','digital_resource','note','question_bank']
    resource_id: int=Field(gt=0)

class ArchiveWrite(BaseModel):
    archived: bool

def get_curriculum(db,id,editable=False):
    row=db.query(Curriculum).filter(Curriculum.id==id).with_for_update().first()
    if not row or row.owner_user_id is not None:raise HTTPException(404,'Curriculum not found')
    if editable and row.archived:raise HTTPException(409,'Archived curricula are read-only; duplicate a version to make changes')
    return row

@router.get('')
def listing(db: Session=Depends(get_db)):
    return db.query(Curriculum).filter(Curriculum.owner_user_id.is_(None)).order_by(Curriculum.college,Curriculum.title,Curriculum.version.desc()).all()

@router.post('',status_code=201)
def create(payload: CurriculumWrite,db: Session=Depends(get_db)):
    row=Curriculum(**payload.model_dump(),family=str(uuid4()),version=1);db.add(row);db.commit();db.refresh(row);return row

@router.get('/{id}')
def detail(id:int,db:Session=Depends(get_db)):
    row=get_curriculum(db,id)
    nodes=db.query(CurriculumNode).filter_by(curriculum_id=id).order_by(CurriculumNode.position,CurriculumNode.id).all()
    mappings=db.query(CurriculumResource).join(CurriculumNode,CurriculumNode.id==CurriculumResource.topic_id).filter(CurriculumNode.curriculum_id==id).all()
    enrollments=db.query(SubjectEnrollment).join(CurriculumNode,CurriculumNode.id==SubjectEnrollment.subject_id).filter(CurriculumNode.curriculum_id==id).all()
    return {'curriculum':row,'nodes':nodes,'mappings':mappings,'enrollments':enrollments}

@router.put('/{id}')
def edit(id:int,payload:CurriculumWrite,db:Session=Depends(get_db)):
    row=get_curriculum(db,id,True)
    for k,v in payload.model_dump().items():setattr(row,k,v)
    db.commit();db.refresh(row);return row

@router.patch('/{id}/archive')
def archive(id:int,payload:ArchiveWrite,db:Session=Depends(get_db)):
    row=get_curriculum(db,id);row.archived=payload.archived;db.commit();return {'archived':row.archived}

@router.post('/{id}/duplicate',status_code=201)
def duplicate(id:int,db:Session=Depends(get_db)):
    source=db.get(Curriculum,id)
    if not source or source.owner_user_id is not None:raise HTTPException(404,'Curriculum not found')
    # Every version shares one lock anchor, avoiding concurrent version numbers.
    anchor=db.query(Curriculum).filter_by(family=source.family).order_by(Curriculum.version).first()
    db.refresh(anchor,with_for_update=True)
    version=(db.query(func.max(Curriculum.version)).filter_by(family=source.family).scalar() or 0)+1
    row=Curriculum(**{k:getattr(source,k) for k in CurriculumWrite.model_fields},family=source.family,version=version,archived=False)
    db.add(row);db.flush();ids={}
    nodes=db.query(CurriculumNode).filter_by(curriculum_id=id).all()
    for kind in ('subject','unit','topic'):
        for old in (n for n in nodes if n.kind==kind):
            new=CurriculumNode(curriculum_id=row.id,parent_id=ids.get(old.parent_id),kind=kind,title=old.title,code=old.code,position=old.position)
            db.add(new);db.flush();ids[old.id]=new.id
    for old in db.query(CurriculumResource).filter(CurriculumResource.topic_id.in_(ids)).all():
        db.add(CurriculumResource(topic_id=ids[old.topic_id],**{k:getattr(old,k) for k in ('book_id','digital_resource_id','note_id','question_bank_id')}))
    db.commit();db.refresh(row);return row

@router.post('/{id}/nodes',status_code=201)
def add_node(id:int,payload:NodeCreate,db:Session=Depends(get_db)):
    get_curriculum(db,id,True)
    parent=db.get(CurriculumNode,payload.parent_id) if payload.parent_id else None
    expected={'unit':'subject','topic':'unit'}.get(payload.kind)
    if (expected and (not parent or parent.curriculum_id!=id or parent.kind!=expected)) or (not expected and parent):
        raise HTTPException(422,'Use subject → unit → topic hierarchy within one curriculum')
    if payload.kind=='subject' and payload.parent_id is not None:raise HTTPException(422,'Subjects have no parent')
    row=CurriculumNode(curriculum_id=id,**payload.model_dump());db.add(row);db.commit();db.refresh(row);return row

@router.put('/nodes/{node_id}')
def edit_node(node_id:int,payload:NodeWrite,db:Session=Depends(get_db)):
    row=db.get(CurriculumNode,node_id)
    if not row:raise HTTPException(404,'Node not found')
    get_curriculum(db,row.curriculum_id,True)
    for k,v in payload.model_dump().items():setattr(row,k,v)
    db.commit();db.refresh(row);return row

@router.post('/topics/{topic_id}/resources',status_code=201)
def map_resource(topic_id:int,payload:MappingWrite,db:Session=Depends(get_db)):
    topic=db.get(CurriculumNode,topic_id)
    if not topic or topic.kind!='topic':raise HTTPException(404,'Topic not found')
    get_curriculum(db,topic.curriculum_id,True)
    model={'book':Book,'digital_resource':DigitalResource,'note':Note,'question_bank':QuestionBank}[payload.kind]
    resource=db.get(model,payload.resource_id)
    if not resource:raise HTTPException(404,'Resource not found')
    if isinstance(resource,Note) and resource.status!='published':raise HTTPException(422,'Only published notes can be mapped')
    if isinstance(resource,DigitalResource) and (not resource.is_published or resource.archived_at is not None or not resource.reviewed_by):raise HTTPException(422,'Publish this resource before mapping it')
    key=payload.kind+'_id';existing=db.query(CurriculumResource).filter_by(topic_id=topic_id,**{key:payload.resource_id}).first()
    if existing:return existing
    row=CurriculumResource(topic_id=topic_id,**{key:payload.resource_id});db.add(row);db.commit();db.refresh(row);return row

@router.delete('/resources/{mapping_id}',status_code=204)
def unmap(mapping_id:int,db:Session=Depends(get_db)):
    row=db.get(CurriculumResource,mapping_id)
    if not row:raise HTTPException(404,'Mapping not found')
    get_curriculum(db,db.get(CurriculumNode,row.topic_id).curriculum_id,True);db.delete(row);db.commit()

@router.put('/subjects/{subject_id}/students/{user_id}')
def enroll(subject_id:int,user_id:int,db:Session=Depends(get_db)):
    subject=db.get(CurriculumNode,subject_id);user=db.get(User,user_id)
    if not subject or subject.kind!='subject' or not user or user.role!=UserRole.STUDENT:raise HTTPException(404,'Subject or student not found')
    get_curriculum(db,subject.curriculum_id,True)
    row=db.query(SubjectEnrollment).filter_by(subject_id=subject_id,user_id=user_id).first()
    if not row:row=SubjectEnrollment(subject_id=subject_id,user_id=user_id);db.add(row)
    db.commit();return {'subject_id':subject_id,'user_id':user_id}
