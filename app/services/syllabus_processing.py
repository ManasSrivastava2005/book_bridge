"""Conservative heading extraction: never infer a hierarchy from arbitrary prose."""
from io import BytesIO
import re
from fastapi import HTTPException
from pypdf import PdfReader
from app.services.book_summarization import extract_text

MAX_BYTES=10*1024*1024
MAX_PAGES=100
MAX_CHARS=300000

def node(title,code=None):return {'id':None,'title':title[:200],'code':code,'objectives':None,'subtopics':[],'children':[]}

def propose_pages(pages,subject_name=None):
    subjects=[];subject=unit=topic=None;evidence=[];unparsed=[];warnings=[]
    if subject_name:
        subject=node(subject_name);subjects.append(subject)
    for page,text in enumerate(pages,1):
        if not text.strip():warnings.append(f'Page {page} has no extractable text; review the original PDF.')
        for number,raw in enumerate(text.splitlines(),1):
            line=raw.strip()
            if not line:continue
            location={'page':page,'line':number,'text':line}
            heading=re.match(r'^(?:subject|course(?:\s+title)?)\s*:\s*(.+)$',line,re.I)
            coded=re.match(r'^([A-Z]{2,5}[- ]?\d{2,4})\s+([A-Za-z].+)$',line)
            unit_heading=re.match(r'^(?:unit|module)\s+([IVX\d]+)\s*[:.\-–]?\s*(.*)$',line,re.I)
            topic_heading=re.match(r'^topic\s*(?:\d+\s*)?[:.\-–]\s*(.+)$',line,re.I) or re.match(r'^\d+\.\d+\s+(.+)$',line)
            if heading or coded:
                title=heading.group(1) if heading else coded.group(2)
                if len(title)>200:unparsed.append(location);warnings.append(f'Page {page}: subject heading is too long; edit it manually.');continue
                if subject_name:
                    # Student-selected subject is authoritative; keep PDF headings as evidence.
                    evidence.append({**location,'detected':'source subject heading'})
                    continue
                subject=node(title,None if heading else coded.group(1));subjects.append(subject);unit=topic=None;evidence.append({**location,'detected':'subject'})
            elif unit_heading and subject:
                title=unit_heading.group(2) or line
                if len(title)>200:unparsed.append(location);continue
                unit=node(title);subject['children'].append(unit);topic=None;evidence.append({**location,'detected':'unit'})
            elif topic_heading and unit:
                title=topic_heading.group(1)
                if len(title)>200:unparsed.append(location);continue
                topic=node(title);unit['children'].append(topic);evidence.append({**location,'detected':'topic'})
            elif re.match(r'^course\s+code\s*:',line,re.I) and subject:
                code=line.split(':',1)[1].strip()
                if len(code)<=50:subject['code']=code;evidence.append({**location,'detected':'course_code'})
                else:unparsed.append(location)
            elif re.match(r'^(?:learning\s+)?objectives?\s*:',line,re.I) and (topic or unit or subject):
                value=line.split(':',1)[1].strip();target=topic or unit or subject
                if len(value)<=2000:target['objectives']=value;evidence.append({**location,'detected':'objectives'})
                else:unparsed.append(location)
            elif re.match(r'^subtopics?\s*:',line,re.I) and topic:
                values=[v.strip() for v in re.split('[,;]',line.split(':',1)[1]) if v.strip()]
                if len(values)<=50 and all(len(v)<=300 for v in values):topic['subtopics']=values;evidence.append({**location,'detected':'subtopics'})
                else:unparsed.append(location)
            elif subject_name and unit and len(line)<=140 and not re.search(r'[.!?]$',line) and not re.match(r'^(?:references|text\s*books|course\s+outcomes|assessment|total\s+hours)\b',line,re.I):
                title=re.sub(r'^[•\-*]\s*','',line)
                topic=node(title);unit['children'].append(topic);evidence.append({**location,'detected':'candidate topic (review required)'})
            else:
                unparsed.append(location)
                if re.match(r'^(?:references|text\s*books|course\s+outcomes|assessment)\b',line,re.I):unit=topic=None
    if not subjects:warnings.append('No explicit subject headings were recognized. Add your subjects, units and topics manually using the extracted text.')
    if unparsed:warnings.append(f'{len(unparsed)} lines were not assigned automatically. Review them before confirmation.')
    warnings.append('Detected headings are a proposal. Check subject boundaries, ordering and missing material before confirming.')
    return {'subjects':subjects,'evidence':evidence,'unparsed':unparsed,'warnings':warnings,'page_count':len(pages)}

def process_pdf(contents,subject_name=None):
    if not contents or len(contents)>MAX_BYTES:raise HTTPException(413,'Upload a non-empty syllabus PDF up to 10 MB.')
    if not contents.startswith(b'%PDF-'):raise HTTPException(400,'Choose a PDF document.')
    try:
        document=PdfReader(BytesIO(contents))
        if document.is_encrypted:raise HTTPException(400,'Upload an unlocked syllabus PDF.')
        if len(document.pages)>MAX_PAGES:raise HTTPException(413,'Syllabus PDFs support at most 100 pages. No pages were discarded.')
        # Share the existing extractor and its malformed/scanned-document safeguards.
        text=extract_text(contents,'.pdf')
        if len(text)>MAX_CHARS:raise HTTPException(413,'Syllabus text exceeds 300,000 characters. Nothing was truncated.')
        pages=[page.extract_text() or '' for page in document.pages]
    except HTTPException:raise
    except Exception:raise HTTPException(400,'The syllabus PDF could not be read.') from None
    return text,propose_pages(pages,subject_name)
