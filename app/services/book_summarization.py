"""Summarization adapted from the supplied book_summarization.py.

All sources share one provider implementation. Uploaded documents are not saved.
"""
from enum import Enum
from io import BytesIO

from fastapi import HTTPException
from pypdf import PdfReader

from app import config

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_INPUT_CHARS = config.LOCAL_SUMMARY_MAX_CHARS


class SummaryMode(str, Enum):
    short = "short"
    detailed = "detailed"
    key_points = "key_points"
    simple = "simple"
    exam_notes = "exam_notes"


def generate_summary(text: str, title: str | None, mode: SummaryMode) -> dict:
    from app.services.summarization_service import summarization_service
    return summarization_service.summarize(text, title, mode)


def extract_text(data: bytes, extension: str) -> str:
    if extension == ".txt":
        try:
            text = data.decode("utf-8-sig")
            if len(text) > MAX_INPUT_CHARS:
                raise HTTPException(413, "This TXT exceeds the local text limit. Submit smaller chapters; nothing was truncated.")
            return text
        except UnicodeDecodeError:
            raise HTTPException(400, "Save your TXT file using UTF-8 encoding and upload it again.") from None
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise HTTPException(400, "Password-protected PDFs are not supported. Upload an unlocked copy.")
        chunks = []
        length = 0
        for page in reader.pages:
            chunk = page.extract_text() or ""
            chunks.append(chunk)
            length += len(chunk) + 1
            if length > MAX_INPUT_CHARS:
                raise HTTPException(413, "This PDF exceeds the local text limit. Submit smaller chapters; nothing was truncated.")
        text = "\n".join(chunks)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "This PDF could not be read. Try another PDF or paste its text.") from None
    if not text.strip():
        raise HTTPException(400, "No readable text was found. Scanned PDFs need OCR first, or you can paste the text.")
    return text
