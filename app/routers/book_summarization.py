"""Authenticated additions; existing /ai routes remain unchanged."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_current_user
from app.services.book_summarization import (
    MAX_INPUT_CHARS, MAX_UPLOAD_BYTES, SummaryMode, extract_text, generate_summary,
)

router = APIRouter(prefix="/ai/summarize", tags=["Book Summarization"], dependencies=[Depends(get_current_user)])


class SummarizeTextRequest(BaseModel):
    text: str = Field(min_length=50, max_length=MAX_INPUT_CHARS)
    title: str | None = Field(default=None, max_length=300)
    mode: SummaryMode = SummaryMode.detailed


class SummaryResponse(BaseModel):
    title: str | None
    mode: SummaryMode
    summary: str
    input_characters: int
    truncated: bool
    model: str
    provider: str
    processing_time: float
    model_load_time: float
    chunks: int
    reduction_passes: int
    warnings: list[str]


@router.post("/text", response_model=SummaryResponse)
def summarize_text(request: SummarizeTextRequest):
    return generate_summary(request.text, request.title, request.mode)


@router.post("/file", response_model=SummaryResponse)
async def summarize_file(
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=300),
    mode: SummaryMode = Form(default=SummaryMode.detailed),
):
    try:
        extension = Path(file.filename or "").suffix.lower()
        if extension not in {".pdf", ".txt"}:
            raise HTTPException(400, "Upload a PDF or TXT file.")
        allowed = {"application/octet-stream", "application/pdf" if extension == ".pdf" else "text/plain"}
        if file.content_type and file.content_type.split(";")[0].lower() not in allowed:
            raise HTTPException(400, "The file type does not match its extension. Upload a PDF or TXT file.")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "The file exceeds the 25 MB limit. Upload a smaller file.")
        if not data:
            raise HTTPException(400, "The uploaded file is empty.")
        text = await run_in_threadpool(extract_text, data, extension)
        return await run_in_threadpool(generate_summary, text, title or (file.filename or "Untitled")[:300], mode)
    finally:
        await file.close()
