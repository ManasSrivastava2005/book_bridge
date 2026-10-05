"""Explainable metadata matching; never claim a resource covers an entire syllabus."""
import re
from app.models.book import Book
from app.models.digital_resource import DigitalResource
from app.models.note import Note
from app.models.question_bank import QuestionBank
from app.models.user import User

STOP={'the','and','for','with','introduction','overview','unit','module','topic','of','to','in'}
def words(text):
    return {w[:-1] if len(w)>4 and w.endswith('s') else w for w in re.findall(r'[a-z0-9]+',(text or '').lower()) if w not in STOP and len(w)>2}
def normalized(text):return ' '.join(re.findall(r'[a-z0-9]+',(text or '').lower()))

def candidates(db,user_id):
    user=db.get(User,user_id);rows=[]
    for model,kind,path in [(Book,'book','/books/'),(DigitalResource,'digital_resource','/reader/'),(Note,'note','/notes'),(QuestionBank,'question_bank','/question-banks')]:
        query=db.query(model)
        if kind=='digital_resource':query=query.filter(model.is_published.is_(True),model.archived_at.is_(None),model.reviewed_by.isnot(None))
        if kind=='note':query=query.filter(model.status=='published',model.access_level=='public')
        for row in query:
            if kind=='digital_resource' and row.access_type=='library_members' and row.library_id!=user.library_id:continue
            metadata=' '.join(str(getattr(row,key,None) or '') for key in ('title','subject','category','description'))
            rows.append((words(metadata),{'id':row.id,'kind':kind,'title':row.title,'url':path+str(row.id) if kind in ('book','digital_resource') else path}))
    return rows

def matches(catalog,subject,topic):
    topic_terms=words(topic);subject_terms=words(subject);result=[]
    for metadata,resource in catalog:
        term=None
        if topic_terms and topic_terms<=metadata and (len(topic_terms)>1 or len(next(iter(topic_terms)))>=4):term=f'topic "{topic}"'
        elif subject_terms and subject_terms<=metadata and (len(subject_terms)>1 or len(next(iter(subject_terms)))>=4):term=f'subject "{subject}"'
        if term:result.append({**resource,'match_reason':'Catalog metadata matches confirmed '+term+'. Review the resource for coverage.'})
    return result[:8]
