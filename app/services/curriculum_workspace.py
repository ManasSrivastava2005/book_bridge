from fastapi import HTTPException
from app.models.curriculum import Curriculum, CurriculumNode
from app.models.user import User
from app.schemas.personal_curriculum import PersonalCurriculumWrite
from app.services.personal_curriculum import get_personal, save_personal

def owned_subject(db, user, subject_id):
    subject = db.query(CurriculumNode).join(Curriculum, Curriculum.id == CurriculumNode.curriculum_id).filter(
        CurriculumNode.id == subject_id, CurriculumNode.kind == 'subject',
        CurriculumNode.archived.is_(False), Curriculum.owner_user_id == user.id,
        Curriculum.archived.is_(False)).first()
    if not subject:
        raise HTTPException(404, 'Subject not found in your personal curriculum.')
    return subject

def subject_topic_ids(db, subject):
    units = db.query(CurriculumNode.id).filter_by(parent_id=subject.id, kind='unit', archived=False)
    return {n.id for n in db.query(CurriculumNode).filter(
        CurriculumNode.parent_id.in_(units), CurriculumNode.kind == 'topic', CurriculumNode.archived.is_(False))}

def update_subject(db, user, subject_id, payload):
    # Same lock order as uploads, exams and whole-curriculum saves.
    db.query(User).filter_by(id=user.id).with_for_update().one()
    subject = owned_subject(db, user, subject_id)
    curriculum = db.get(Curriculum, subject.curriculum_id)
    if curriculum.version != payload.expected_version:
        raise HTTPException(409, 'Curriculum changed. Reload before saving your edits.')
    tree = get_personal(db, user, curriculum.semester)
    item = payload.subject.model_dump()
    if item['id'] not in (None, subject_id):
        raise HTTPException(422, 'Cannot replace another subject.')
    # Prevent moving IDs from sibling subjects through a subject-scoped editor.
    current = next(s for s in tree['subjects'] if s['id'] == subject_id)
    def ids(node):
        return ({node['id']} if node['id'] else set()).union(*(ids(c) for c in node['children']))
    if ids(item) - ids(current):
        raise HTTPException(422, 'A node belongs to another subject.')
    item['id'] = subject_id
    tree['subjects'] = [item if s['id'] == subject_id else s for s in tree['subjects']]
    save_personal(db, user, PersonalCurriculumWrite.model_validate(tree))
    return subject
