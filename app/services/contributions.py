"""Private storage shared by moderation and a future student submission flow."""
import io
import re
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
PRIVATE_DIR=ROOT/'private_uploads'/'contributions'
PUBLIC_DIR=ROOT/'uploads'/'contributions'

def private_path(name):
    if not re.fullmatch(r'[a-f0-9]{32}\.(pdf|txt)',name):
        raise HTTPException(422,'Invalid contribution file reference')
    return PRIVATE_DIR/name

def store_pending_file(filename: str, content: bytes):
    extension=Path(filename).suffix.lower()
    if extension not in ('.pdf','.txt') or not content or len(content)>25*1024*1024:
        raise HTTPException(422,'Use a nonempty PDF or UTF-8 text file up to 25 MB')
    try:
        if extension=='.pdf':
            pdf=PdfReader(io.BytesIO(content))
            if not content.startswith(b'%PDF-') or pdf.is_encrypted or not len(pdf.pages): raise ValueError()
        else: content.decode('utf-8')
    except Exception:
        raise HTTPException(422,'The file could not be read')
    PRIVATE_DIR.mkdir(parents=True,exist_ok=True)
    name=uuid4().hex+extension
    try:
        private_path(name).write_bytes(content)
    except OSError:
        private_path(name).unlink(missing_ok=True)
        raise HTTPException(500, "Unable to store the contribution file") from None
    return name
