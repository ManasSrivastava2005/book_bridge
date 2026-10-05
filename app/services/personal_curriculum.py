from uuid import uuid4
from fastapi import HTTPException
from app.models.user import User
from app.models.curriculum import Curriculum,CurriculumNode
from app.models.academic_profile import AcademicProfile
from app.services.student_curriculum import sync_enrollment

def selected_semester(db,user,semester=None):
    if semester is not None:return semester
    profile=db.get(AcademicProfile,user.id)
    active=db.get(Curriculum,profile.curriculum_id) if profile and profile.curriculum_id else None
    return active.semester if active and active.owner_user_id==user.id else user.semester or 1

def get_personal(db,user,semester=None):
    semester=selected_semester(db,user,semester)
    row=db.query(Curriculum).filter_by(owner_user_id=user.id,semester=semester).first()
    if not row:
        profile=db.get(AcademicProfile,user.id)
        return {'semester':semester,'curriculum_id':None,'expected_version':0,'title':'My curriculum','subjects':[{'id':None,'title':title,'code':None,'objectives':None,'subtopics':[],'children':[]} for title in (profile.custom_subjects or [] if profile else [])]}
    nodes=db.query(CurriculumNode).filter_by(curriculum_id=row.id,archived=False).order_by(CurriculumNode.position,CurriculumNode.id).all()
    def children(parent):
        return [{'id':n.id,'title':n.title,'code':n.code,'objectives':n.objectives,'subtopics':n.subtopics or [],'children':children(n.id)} for n in nodes if n.parent_id==parent]
    return {'semester':row.semester,'curriculum_id':row.id,'expected_version':row.version,'title':row.title,'subjects':children(None)}

def save_personal(db,user,payload):
    """Caller commits. Stable node IDs retain exams, topic progress and task history."""
    db.query(User).filter_by(id=user.id).with_for_update().one()
    semester=selected_semester(db,user,payload.semester)
    row=db.query(Curriculum).filter_by(owner_user_id=user.id,semester=semester).with_for_update().first()
    if row:
        if payload.curriculum_id!=row.id or payload.expected_version!=row.version:raise HTTPException(409,'Curriculum changed. Reload before saving your edits.')
    elif payload.curriculum_id or payload.expected_version:raise HTTPException(404,'Personal curriculum not found')
    profile=db.get(AcademicProfile,user.id)
    if not profile:profile=AcademicProfile(user_id=user.id,subject_ids=[],custom_subjects=[]);db.add(profile)
    if not row:
        row=Curriculum(owner_user_id=user.id,family=str(uuid4()),version=1,title=payload.title,college=profile.college or '',program=profile.program or '',branch=user.branch or '',semester=semester)
        db.add(row);db.flush()
    else:row.version+=1;row.title=payload.title;row.archived=False
    existing={n.id:n for n in db.query(CurriculumNode).filter_by(curriculum_id=row.id)}
    seen=set();subjects=[]
    def save(nodes,parent,depth):
        kind=('subject','unit','topic')[depth]
        for position,item in enumerate(nodes):
            node=existing.get(item.id) if item.id else None
            if item.id and (not node or node.kind!=kind):raise HTTPException(422,'Node does not belong to this personal curriculum or level')
            if not node and not item.id:
                matches=[n for n in existing.values() if n.id not in seen and n.kind==kind and n.parent_id==parent and (depth!=0 or not n.archived) and n.title.strip().casefold()==item.title.casefold()]
                if len(matches)==1:node=matches[0]
            if not node:node=CurriculumNode(curriculum_id=row.id,kind=kind);db.add(node)
            node.title=item.title;node.code=item.code;node.objectives=item.objectives;node.subtopics=item.subtopics
            node.parent_id=parent;node.position=position;node.archived=False
            db.flush();seen.add(node.id)
            if depth==0:subjects.append(node.id)
            if item.children:save(item.children,node.id,depth+1)
    save(payload.subjects,None,0)
    for node in existing.values():
        if node.id not in seen:node.archived=True
    sync_enrollment(db,user.id,profile.subject_ids or [],subjects)
    profile.curriculum_id=row.id;profile.subject_ids=subjects
    user.semester=row.semester
    db.flush()
    return row

def activate_semester(db,user,semester):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    row=db.query(Curriculum).filter_by(owner_user_id=user.id,semester=semester,archived=False).first()
    if not row:raise HTTPException(404,'Save a curriculum for this semester first.')
    profile=db.get(AcademicProfile,user.id)
    if not profile:profile=AcademicProfile(user_id=user.id,subject_ids=[],custom_subjects=[]);db.add(profile)
    subjects=[n.id for n in db.query(CurriculumNode).filter_by(curriculum_id=row.id,kind='subject',archived=False)]
    sync_enrollment(db,user.id,profile.subject_ids or [],subjects)
    profile.curriculum_id=row.id;profile.subject_ids=subjects;user.semester=semester
    db.flush()
