"""Runtime configuration, loaded from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# .env at project root wins, backend/.env as fallback.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = _int("OLLAMA_TIMEOUT", 120)

MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 15)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Hard caps so a huge document cannot stall the demo laptop.
MAX_PAGES = _int("MAX_PAGES", 40)
OCR_MAX_PAGES = _int("OCR_MAX_PAGES", 8)
OCR_DPI = _int("OCR_DPI", 200)
OCR_MAX_IMAGE_PX = _int("OCR_MAX_IMAGE_PX", 2200)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
OCR_LANGS = os.getenv("OCR_LANGS", "eng").strip()

# How many flagged clauses get an LLM explanation (one batched call).
MAX_EXPLAINED_CLAUSES = _int("MAX_EXPLAINED_CLAUSES", 8)
# Characters of clause text sent per clause.
MAX_CLAUSE_CHARS = _int("MAX_CLAUSE_CHARS", 700)
# Characters of retrieved context sent for a question.
MAX_QA_CONTEXT_CHARS = _int("MAX_QA_CONTEXT_CHARS", 3500)

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    ).split(",")
    if o.strip()
]

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

# Set true only if you want extracted text echoed into server logs. Off by default:
# documents are sensitive.
LOG_DOCUMENT_TEXT = _bool("LOG_DOCUMENT_TEXT", False)
