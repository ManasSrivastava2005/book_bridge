from fastapi import HTTPException
from app.models.academic_profile import AcademicProfile
from app.models.curriculum import Curriculum,CurriculumNode,CurriculumResource,SubjectEnrollment
from app.models.topic_progress import TopicProgress
from app.models.book import Book
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.digital_resource import DigitalResource

def curriculum_data(db,user_id,curriculum_id=None):
    profile=db.get(AcademicProfile,user_id)
    if not curriculum_id and (not profile or not profile.curriculum_id):return {'curriculum':None,'subjects':[],'custom_subjects':profile.custom_subjects if profile else []}
    c=db.get(Curriculum,curriculum_id or profile.curriculum_id)
    if not c or c.owner_user_id not in (None,user_id):raise HTTPException(404,'Curriculum not found')
    nodes=db.query(CurriculumNode).filter_by(curriculum_id=c.id,archived=False).order_by(CurriculumNode.position,CurriculumNode.id).all()
    done={row.topic_id for row in db.query(TopicProgress).filter_by(user_id=user_id)}
    from app.services.curriculum_matching import candidates,matches
    catalog=candidates(db,user_id) if c.owner_user_id==user_id else []
    subjects=[]
    for s in nodes:
        if s.kind!='subject' or (not curriculum_id and s.id not in profile.subject_ids):continue
        units=[];topics=[]
        for unit in [n for n in nodes if n.parent_id==s.id and n.kind=='unit']:
            children=[]
            for t in [n for n in nodes if n.parent_id==unit.id and n.kind=='topic']:
                resources=[]
                for mapping in db.query(CurriculumResource).filter_by(topic_id=t.id):
                    for field,kind,model,path in [('book_id','book',Book,'/books/'),('digital_resource_id','digital_resource',DigitalResource,'/reader/'),('note_id','note',Note,'/notes'),('question_bank_id','question_bank',QuestionBank,'/question-banks')]:
                        rid=getattr(mapping,field)
                        if rid:
                            r=db.get(model,rid)
                            if not r or kind=='note' and r.status!='published' or kind=='digital_resource' and (not r.is_published or r.archived_at is not None or not r.reviewed_by):continue
                            resources.append({'id':rid,'kind':kind,'title':r.title,'url':path+str(rid) if kind in ('book','digital_resource') else path})
                if catalog:
                    known={(r['kind'],r['id']) for r in resources}
                    resources.extend(r for r in matches(catalog,s.title,t.title) if (r['kind'],r['id']) not in known)
                item={'id':t.id,'title':t.title,'objectives':t.objectives,'subtopics':t.subtopics or [],'completed':t.id in done,'resources':resources};children.append(item);topics.append(item)
            units.append({'id':unit.id,'title':unit.title,'topics':children})
        count=sum(t['completed'] for t in topics)
        subjects.append({'id':s.id,'title':s.title,'units':units,'completed_topics':count,'total_topics':len(topics),'progress_percent':round(count/len(topics)*100,1) if topics else 0})
    return {'curriculum':{'id':c.id,'title':c.title,'version':c.version,'archived':c.archived,'personal':c.owner_user_id==user_id},'subjects':subjects,'custom_subjects':profile.custom_subjects}

def selected_topic(db,user_id,topic_id):
    for subject in curriculum_data(db,user_id)['subjects']:
        if any(t['id']==topic_id for u in subject['units'] for t in u['topics']):return subject
    raise HTTPException(404,'Topic is not in your selected subjects')

def sync_enrollment(db,user_id,old_ids,new_ids):
    for sid in set(old_ids)-set(new_ids):
        db.query(SubjectEnrollment).filter_by(user_id=user_id,subject_id=sid).delete()
    for sid in set(new_ids):
        if not db.query(SubjectEnrollment).filter_by(user_id=user_id,subject_id=sid).first():db.add(SubjectEnrollment(user_id=user_id,subject_id=sid))
