from datetime import datetime,timezone,timedelta
from sqlalchemy import or_
from app.models.academic_task import AcademicTask
from app.models.topic_progress import TopicProgress
from app.models.student_exam import StudentExam
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.reader_state import ReaderState
from app.models.user import User
from app.models.curriculum import CurriculumNode
from app.services.curriculum_matching import normalized
from app.services.student_curriculum import curriculum_data

def today_utc():return datetime.now(timezone.utc).date()

def generate_plan(db,user_id,daily_minutes=120):
    db.query(User).filter_by(id=user_id).with_for_update().one()
    today=today_utc();curriculum=curriculum_data(db,user_id)
    exams=db.query(StudentExam).filter(StudentExam.user_id==user_id,StudentExam.date>=today).order_by(StudentExam.date,StudentExam.id).all()
    existing={r.event_key:r for r in db.query(AcademicTask).filter_by(user_id=user_id)}
    done={r.topic_id:r.completed_at for r in db.query(TopicProgress).filter_by(user_id=user_id)}
    reader={r.resource_id:r.data for r in db.query(ReaderState).filter_by(user_id=user_id)}
    completed_quizzes={r.quiz_id:r.submitted_at for r in db.query(QuizAttempt).filter(QuizAttempt.user_id==user_id,QuizAttempt.submitted_at.isnot(None)).order_by(QuizAttempt.submitted_at.desc())}
    published_quizzes=db.query(Quiz).filter(Quiz.status=='published',Quiz.active.is_(True),Quiz.permission_confirmed.is_(True)).all()
    quiz_nodes={n.id:n for n in db.query(CurriculumNode).filter(CurriculumNode.id.in_({i for q in published_quizzes for i in (q.subject_id,q.topic_id) if i}))}
    used_quizzes=set()
    tasks=[]
    for subject in curriculum['subjects']:
        exam=next((e for e in exams if e.subject_id==subject['id']),None)
        deadline=exam.date if exam else today+timedelta(days=6)
        for unit in subject['units']:
            for topic in unit['topics']:
                specs=[(f'topic:{topic["id"]}:study','read' if topic['resources'] else 'practice',None)]
                if exam:specs.append((f'topic:{topic["id"]}:revision','revision',None))
                quizzes=[]
                for q in published_quizzes:
                    same=q.topic_id==topic['id']
                    if not same and curriculum['curriculum'] and curriculum['curriculum'].get('personal'):
                        qt=quiz_nodes.get(q.topic_id);qs=quiz_nodes.get(q.subject_id)
                        same=bool(qt and qs and normalized(qt.title)==normalized(topic['title']) and normalized(qs.title)==normalized(subject['title']))
                    if same and q.id not in used_quizzes:quizzes.append(q);used_quizzes.add(q.id)
                specs += [(f'quiz:{q.id}','quiz',q.id) for q in quizzes]
                progress=0
                for resource in topic['resources']:
                    data=reader.get(resource['id']) if resource['kind']=='digital_resource' else None
                    if data and data.get('total_pages',0)>0:progress=max(progress,min(1,data.get('page',1)/data['total_pages']))
                for key,kind,quiz_id in specs:
                    row=existing.get(key)
                    if not row:
                        row=AcademicTask(user_id=user_id,topic_id=topic['id'],quiz_id=quiz_id,event_key=key,kind=kind,estimated_minutes=30);db.add(row);existing[key]=row
                    if kind in ('read','practice'):row.completed_at=done.get(topic['id'])
                    if kind=='quiz' and quiz_id in completed_quizzes:row.completed_at=completed_quizzes[quiz_id]
                    if not row.completed_at:row.estimated_minutes=15 if kind in ('revision','quiz') else max(10,round(30*(1-progress)))
                    tasks.append((row,subject,topic,deadline,exam))
    capacity={};overflow=0
    for row,subject,topic,deadline,exam in sorted(tasks,key=lambda x:(x[3],x[1]['id'],x[2]['id'],{'read':0,'practice':0,'quiz':1,'revision':2}[x[0].kind])):
        if row.completed_at:continue
        row.due_date=None
        horizon=min(366,max(1,(deadline-today).days+1))
        for offset in range(horizon):
            day=today+timedelta(days=offset)
            if capacity.get(day,0)+row.estimated_minutes<=daily_minutes:
                row.due_date=day;capacity[day]=capacity.get(day,0)+row.estimated_minutes;break
        if row.due_date is None:overflow+=1
    db.flush()
    result={'today':today,'daily_minutes':daily_minutes,'subjects':curriculum['subjects'],'custom_subjects':curriculum['custom_subjects'],
            'exams':[{'id':e.id,'name':e.name,'subject_id':e.subject_id,'subject':e.custom_subject or next((s['title'] for s in curriculum['subjects'] if s['id']==e.subject_id),'Previous subject'),'date':e.date,'days_remaining':(e.date-today).days} for e in exams],
            'warning':'Your remaining syllabus may require more study time than the available days.' if overflow else None,'unscheduled_tasks':overflow,
            'tasks':[{'id':r.id,'kind':r.kind,'topic_id':t['id'],'topic':t['title'],'subject':s['title'],'subject_id':s['id'],'quiz_id':r.quiz_id,'due_date':r.due_date,'completed':r.completed_at is not None,'estimated_minutes':r.estimated_minutes,'resources':t['resources']} for r,s,t,d,e in tasks]}
    return result
