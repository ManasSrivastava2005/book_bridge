# Gemini summarization migration

> Historical report. Summarization now runs locally with FLAN-T5 Base, without cloud fallback. See `LOCAL_SUMMARIZER_REPORT.md` and `LOCAL_SUMMARIZER_SETUP.md` for the active implementation. This Gemini implementation is retained in `app/services/cloud_book_summarization.py`.

## Files modified

- `app/services/book_summarization.py`: Gemini SDK client, response validation and sanitized error mapping.
- `app/config.py`: server-only GEMINI_API_KEY and configurable Gemini model default.
- `requirements.txt`: google-genai>=2.24.0,<3 (installed 2.24.0).
- `.env.example`: Gemini settings; previous optional OpenAI setting retained.
- `.env`: summary model set to gemini-3.1-flash-lite; key value was not changed or displayed.
- `test_book_summarization.py`: Gemini provider mocks and error cases.
- `verify_summarization_live.py`: Gemini response fixture and guard against running the unconfigured-provider browser harness on a configured server.
- `PHASE3_REPORT.md`: marked original report as historical.

## Provider before

OpenAI for Book Summarizer. Its usage-limit message represented a provider rate/quota error; the message alone did not distinguish billing exhaustion from temporary throttling.

## Provider after

Gemini for Book Summarizer only, using Google's [google-genai SDK](https://github.com/googleapis/python-genai). API calls remain on FastAPI; no key is sent to React. JWT, existing endpoint contracts, all five modes, PDF/TXT extraction, 25 MiB upload limit and UI are preserved.

The configured project's model list was checked. gemini-flash-latest and gemini-3.5-flash returned provider 503 errors during verification; gemini-2.5-flash returned 404 despite appearing in the model list. gemini-3.1-flash-lite successfully generated content and is now the configured/default model. Override using BOOKBRIDGE_SUMMARY_MODEL on the backend.

## AI Assistant

The existing assistant is catalog-based, not OpenAI-powered. Its code was unchanged and its authenticated live `/ai/chat` request returned 200. Existing OpenAI configuration/dependency was retained; the summarizer no longer calls it.

## Test results

- 33 automated tests passed: all five summary modes, real PDF text extraction, TXT, input/file validation, upload limit, JWT authentication, missing configuration, Gemini 400/401/403/404/429/500/504 errors, transport failures, incomplete/blocked responses, existing AI routes, and Notes regressions.
- Actual authenticated calls through the restarted backend: text 200, TXT 200, PDF 200, each returning nonempty Gemini summaries. Synthetic operating-system text was used; no existing records were changed.
- Backend health 200 and existing chat 200.
- `pip check`: no broken requirements.
- No frontend files changed. The earlier browser checks remain historical; the migration was verified through actual HTTP API requests and automated regressions.

The backend is running on http://127.0.0.1:8000. Gemini availability and quotas can still cause provider errors, which are displayed without exposing raw provider details or logging the user out.
