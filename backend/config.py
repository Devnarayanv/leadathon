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
OLLAMA_TIMEOUT = _int("OLLAMA_TIMEOUT", 240)

# A model that fits entirely in VRAM is several times faster than one that
# spills to CPU. A small model is plenty for English, while Malayalam needs a
# larger multilingual one, so the two can be configured separately and the slow
# model is only loaded when the user actually asks for Malayalam.
OLLAMA_MODEL_ML = os.getenv("OLLAMA_MODEL_ML", "").strip()
# The Malayalam model is bigger and may spill to CPU, so it gets its own,
# longer budget instead of failing a request that was going to succeed.
OLLAMA_TIMEOUT_ML = _int("OLLAMA_TIMEOUT_ML", 420)


def model_for(language: str) -> str:
    if language == "ml" and OLLAMA_MODEL_ML:
        return OLLAMA_MODEL_ML
    return OLLAMA_MODEL


def timeout_for(language: str) -> int:
    if language == "ml" and OLLAMA_MODEL_ML and OLLAMA_MODEL_ML != OLLAMA_MODEL:
        return OLLAMA_TIMEOUT_ML
    return OLLAMA_TIMEOUT
# How long Ollama keeps the model in memory after a request. Without this it
# unloads after ~5 idle minutes and the next upload pays a full cold load.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
# Budget for the one-off model load at server startup.
OLLAMA_WARMUP_TIMEOUT = _int("OLLAMA_WARMUP_TIMEOUT", 300)

MAX_UPLOAD_MB = _int("MAX_UPLOAD_MB", 15)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Hard caps so a huge document cannot stall the demo laptop.
MAX_PAGES = _int("MAX_PAGES", 40)
OCR_MAX_PAGES = _int("OCR_MAX_PAGES", 8)
OCR_DPI = _int("OCR_DPI", 220)
OCR_MAX_IMAGE_PX = _int("OCR_MAX_IMAGE_PX", 2600)
# Images smaller than this on the long edge are enlarged before recognition.
# Screenshots and web-sized photos are the common case and they are far below
# the ~300 DPI Tesseract expects, which is why they used to read as noise.
OCR_MIN_IMAGE_PX = _int("OCR_MIN_IMAGE_PX", 1800)
# Past this factor, upscaling invents edges instead of recovering them.
OCR_MAX_UPSCALE = float(os.getenv("OCR_MAX_UPSCALE", "4") or 4)
# Page-segmentation modes to try per image (see PSM_MODES in ocr_reader).
OCR_PASSES = _int("OCR_PASSES", 3)
# A first pass scoring at least this is kept without trying the others.
OCR_GOOD_ENOUGH_SCORE = _int("OCR_GOOD_ENOUGH_SCORE", 900)
# How much better a multi-script pass must score to displace the English-only
# one. 1.0 would let a tie through; a tie means the extra script added nothing.
OCR_LANG_SWITCH_MARGIN = float(os.getenv("OCR_LANG_SWITCH_MARGIN", "1.08") or 1.08)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
OCR_LANGS = os.getenv("OCR_LANGS", "eng+mal").strip()

# Extra language packs (for example Malayalam) can live in a project folder, so
# no administrator rights are needed to add one. If TESSDATA_DIR is unset and
# <project>/tessdata exists, it is used automatically. A directory given here
# REPLACES Tesseract's own, so it must hold every language in OCR_LANGS.
_tessdata = os.getenv("TESSDATA_DIR", "").strip()
if not _tessdata and (PROJECT_ROOT / "tessdata").is_dir():
    _tessdata = str(PROJECT_ROOT / "tessdata")
TESSDATA_DIR = _tessdata

# Offline speech synthesis (eSpeak NG). Optional: the browser's own voices
# are tried first, and this only covers languages it has no voice for.
ESPEAK_CMD = os.getenv("ESPEAK_CMD", "").strip()

# How many flagged clauses get an LLM explanation (one batched call).
MAX_EXPLAINED_CLAUSES = _int("MAX_EXPLAINED_CLAUSES", 6)
# The Malayalam model is usually the larger, slower one, so it explains fewer
# clauses per request. The rest still show rule-based notes, and the UI says so.
MAX_EXPLAINED_CLAUSES_ML = _int("MAX_EXPLAINED_CLAUSES_ML", 3)


def max_explained_for(language: str) -> int:
    if language == "ml" and OLLAMA_MODEL_ML and OLLAMA_MODEL_ML != OLLAMA_MODEL:
        return MAX_EXPLAINED_CLAUSES_ML
    return MAX_EXPLAINED_CLAUSES
# Output tokens allowed per clause. Generation time is dominated by this,
# so trimming it is the cheapest way to make a demo feel responsive.
CLAUSE_TOKEN_BUDGET = _int("CLAUSE_TOKEN_BUDGET", 170)
# Malayalam text costs far more tokens per sentence than English, so the same
# budget truncates the JSON mid-object and the whole reply is wasted.
CLAUSE_TOKEN_BUDGET_ML = _int("CLAUSE_TOKEN_BUDGET_ML", 340)


def clause_token_budget_for(language: str) -> int:
    return CLAUSE_TOKEN_BUDGET_ML if language == "ml" else CLAUSE_TOKEN_BUDGET
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

# Expose the interactive API schema at /docs. Off by default so a deployment
# does not publish a map of every endpoint and payload.
ENABLE_API_DOCS = _bool("ENABLE_API_DOCS", False)
