"""A live, topic-scoped path. Historical AcademicTask records are not mutated."""
from datetime import datetime, timezone, timedelta
from app.models.academic_profile import AcademicProfile
from app.models.student_exam import StudentExam
from app.services.student_curriculum import curriculum_data

def build_path(db, user_id, curriculum_id=None):
    data = curriculum_data(db, user_id, curriculum_id)
    today = datetime.now(timezone.utc).date()
    profile = db.get(AcademicProfile, user_id)
    minutes = profile.daily_minutes if profile else 60
    exams = db.query(StudentExam).filter(StudentExam.user_id == user_id, StudentExam.date >= today).order_by(StudentExam.date, StudentExam.id).all()
    steps = []
    for subject in data['subjects']:
        for unit in subject['units']:
            for topic in unit['topics']:
                exam = next((e for e in exams if e.subject_id == subject['id'] and topic['id'] in (e.topic_ids or [])), None)
                steps.append({**topic, 'subject_id': subject['id'], 'subject': subject['title'], 'unit': unit['title'],
                              'exam_date': exam.date if exam else None, 'exam_name': exam.name if exam else None,
                              'estimated_minutes': 30, 'scheduled_date': None, 'session_minutes': 0})
    # Stable syllabus order within each deadline; uncovered material follows exam coverage.
    steps.sort(key=lambda s: (s['completed'], s['exam_date'] is None, s['exam_date'] or today))
    used = 0
    late = 0
    next_found = False
    for step in steps:
        step['status'] = 'completed' if step['completed'] else 'upcoming' if next_found else 'next'
        step['deadline_at_risk'] = False
        if step['completed']:
            continue
        next_found = True
        step['scheduled_date'] = today + timedelta(days=used // minutes)
        step['session_minutes'] = min(30, minutes - used % minutes)
        used += 30
        finish = today + timedelta(days=(used - 1) // minutes)
        step['finish_date'] = finish
        step['deadline_at_risk'] = bool(step['exam_date'] and finish > step['exam_date'])
        late += int(step['deadline_at_risk'])
    return {'curriculum': data['curriculum'], 'steps': steps, 'daily_minutes': minutes,
            'warning': f'{late} topics may finish after their exam. Increase study time or adjust coverage.' if late else None,
            'estimate_note': 'Estimated at 30 minutes per topic; longer topics can span study days.',
            'coverage_missing': sum(e.topic_ids is None or not e.topic_ids for e in exams if e.subject_id in {s['id'] for s in data['subjects']})}
