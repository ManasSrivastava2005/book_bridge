from datetime import datetime,timezone
from sqlalchemy import func
from app.models.book import Book
from app.models.review import Review
from app.models.borrow import BorrowRecord
from app.models.student_exam import StudentExam
from app.services.student_curriculum import curriculum_data

def recommendations(db,user):
    today=datetime.now(timezone.utc).date();curriculum=curriculum_data(db,user.id)
    deadlines={}
    for exam in db.query(StudentExam).filter(StudentExam.user_id==user.id,StudentExam.date>=today).order_by(StudentExam.date):
        for topic_id in exam.topic_ids or []:
            deadlines.setdefault((exam.subject_id,topic_id),(exam.date,exam.name))
    relevance={}
    for subject in curriculum['subjects']:
        for unit in subject['units']:
            for topic in unit['topics']:
                for resource in topic['resources']:
                    if resource['kind']=='book':relevance.setdefault(resource['id'],[]).append((subject,{**topic,'match_reason':resource.get('match_reason')}))
    categories={row[0] for row in db.query(Book.category).join(BorrowRecord,BorrowRecord.book_id==Book.id).filter(BorrowRecord.user_id==user.id).distinct() if row[0]}
    ratings={bid:(float(avg),count) for bid,avg,count in db.query(Review.book_id,func.avg(Review.rating),func.count(Review.id)).group_by(Review.book_id)}
    result=[]
    for book in db.query(Book).all():
        links=relevance.get(book.id,[]);reasons=[]
        curriculum_score=40 if any(not t['completed'] for s,t in links) else 20 if links else 0
        if links:reasons.append(links[0][1].get('match_reason') or ('Mapped to '+links[0][0]['title']+' curriculum'+(' and an incomplete topic' if curriculum_score==40 else ' for revision')))
        urgent=[(deadlines[(s['id'],t['id'])],s['title']) for s,t in links if (s['id'],t['id']) in deadlines]
        urgency=0
        if urgent:
            (date,name),subject=min(urgent,key=lambda item:item[0][0]);days=(date-today).days
            urgency=25*max(0,1-days/30)
            if urgency:reasons.append(f'{subject}: {name} in {days} days')
        history=15 if book.category and book.category in categories else 0
        if history:reasons.append('Matches a category in your borrowing history')
        available=10 if book.available_copies>0 else 0
        if available:reasons.append('Copies available in the catalogue')
        avg,count=ratings.get(book.id,(0,0));rating=10*avg/5
        if count:reasons.append(f'{count} recorded review'+('s' if count!=1 else ''))
        if not reasons:reasons.append('Catalogue option; add curriculum subjects for more relevant suggestions')
        result.append({'id':book.id,'title':book.title,'author':book.author,'category':book.category,'cover_image':book.cover_image,'available_copies':book.available_copies,'average_rating':round(avg,1),'review_count':count,'score':round(curriculum_score+urgency+history+available+rating,1),'score_breakdown':{'curriculum':curriculum_score,'exam':round(urgency,1),'history':history,'availability':available,'rating':round(rating,1)},'reasons':reasons})
    return sorted(result,key=lambda r:(-r['score'],r['id']))[:20]
