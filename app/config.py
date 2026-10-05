import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from the .env file into the environment.
# This means os.getenv("DATABASE_URL") will now return the value from .env
load_dotenv()

# Optional server-only summarization configuration.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
BOOKBRIDGE_SUMMARY_MODEL = os.getenv("BOOKBRIDGE_SUMMARY_MODEL", "gemini-3.1-flash-lite").strip() or "gemini-3.1-flash-lite"

# Active summarizer is local only. Cloud settings above are retained for the
# archived implementation, never selected as a fallback.
LOCAL_SUMMARY_MODEL_NAME = os.getenv("LOCAL_SUMMARY_MODEL_NAME", "google/flan-t5-base")
LOCAL_SUMMARY_MODEL_PATH = os.getenv("LOCAL_SUMMARY_MODEL_PATH", str(Path(__file__).resolve().parent.parent / "models" / "flan-t5-base"))
LOCAL_SUMMARY_THREADS = max(1, min(6, int(os.getenv("LOCAL_SUMMARY_THREADS", "4"))))
LOCAL_SUMMARY_CHUNK_TOKENS = 400
LOCAL_SUMMARY_MAX_CHARS = 1_000_000
LOCAL_SUMMARY_MAX_CHUNKS = 512
LOCAL_SUMMARY_TIMEOUT_SECONDS = 600

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./book_bridge.db")

# JWT (authentication) settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "book-bridge-secure-development-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"  # The hashing algorithm used to sign tokens
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))
LOAN_RENEWAL_DAYS = max(1, int(os.getenv('LOAN_RENEWAL_DAYS', '14')))
LOAN_MAX_RENEWALS = max(0, int(os.getenv('LOAN_MAX_RENEWALS', '2')))

# Frontend origins allowed to call this API from a browser during local
# development. Override with a comma-separated CORS_ORIGINS value when the
# frontend is deployed or uses a different port.
DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "*",
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",")
    if origin.strip()
]
