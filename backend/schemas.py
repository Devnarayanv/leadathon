"""Pydantic models for API requests, responses and validated LLM output."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Language = Literal["en", "ml"]


class Segment(BaseModel):
    """One sentence/clause-sized chunk of the document, with its origin."""

    id: int
    text: str
    page: Optional[int] = None


class PageText(BaseModel):
    page: int
    text: str
    source: Literal["pdf_text", "ocr", "empty"] = "pdf_text"


class Fact(BaseModel):
    key: str
    label: str
    value: str
    page: Optional[int] = None
    source_text: Optional[str] = None
    confidence: Literal["high", "medium", "low"] = "medium"
    uncertain: bool = False


class ClauseExplanation(BaseModel):
    """Validated LLM output for a single clause. All fields optional-safe."""

    what_it_says: str = ""
    plain_meaning: str = ""
    why_pay_attention: str = ""
    next_step: str = ""
    uncertain: str = ""
    source: Literal["llm", "rules"] = "rules"
    language: Language = "en"


class Clause(BaseModel):
    id: int
    category: str
    label: str
    attention_level: Literal["info", "attention", "financial", "deadline", "unusual"]
    text: str
    page: Optional[int] = None
    reason: str
    confidence: Literal["high", "medium", "low"]
    matched_terms: List[str] = Field(default_factory=list)
    suggested_action: str = ""
    explanation: Optional[ClauseExplanation] = None


class Deadline(BaseModel):
    id: int
    date_iso: Optional[str] = None
    date_text: str
    description: str
    source_text: str
    page: Optional[int] = None
    confidence: Literal["high", "medium", "low"]
    verified: bool = False


class Classification(BaseModel):
    doc_type: str
    label: str
    certain: bool
    score: int = 0
    matched_terms: List[str] = Field(default_factory=list)


class OllamaStatus(BaseModel):
    reachable: bool
    model: str
    model_available: bool
    base_url: str
    message: str = ""
    models_installed: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    analysis_id: str
    filename: str
    file_size_bytes: int
    page_count: int
    classification: Classification
    language: Language = "en"
    extraction_sources: List[str] = Field(default_factory=list)
    ocr_used: bool = False
    ocr_available: bool = True
    ocr_message: str = ""
    text_chars: int = 0
    facts: List[Fact] = Field(default_factory=list)
    clauses: List[Clause] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    segments: List[Segment] = Field(default_factory=list)
    pages: List[PageText] = Field(default_factory=list)
    summary: str = ""
    summary_source: Literal["llm", "rules"] = "rules"
    ollama: OllamaStatus
    warnings: List[str] = Field(default_factory=list)
    attention_counts: dict = Field(default_factory=dict)
    duration_ms: int = 0


class Evidence(BaseModel):
    text: str
    page: Optional[int] = None
    score: float = 0.0


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    segments: List[Segment] = Field(default_factory=list, max_length=4000)
    doc_type: str = "other"
    language: Language = "en"


class AskResponse(BaseModel):
    answer: str
    evidence: List[Evidence] = Field(default_factory=list)
    grounded: bool
    source: Literal["llm", "rules", "none"] = "none"
    language: Language = "en"


class CalendarDeadline(BaseModel):
    date_iso: str
    description: str
    source_text: str = ""
    page: Optional[int] = None


class CalendarRequest(BaseModel):
    filename: str = "document"
    deadlines: List[CalendarDeadline] = Field(min_length=1, max_length=50)
    # Days before the date to fire the reminder. 0 means on the day itself.
    reminder_days: int = Field(default=3, ge=0, le=60)


class ExplainRequest(BaseModel):
    """Re-explain already-detected clauses, e.g. after starting Ollama
    or switching language. No re-upload needed."""

    doc_type: str = "other"
    language: Language = "en"
    clauses: List[Clause] = Field(min_length=1, max_length=25)


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    language: Language = "en"


class ExplainResponse(BaseModel):
    clauses: List[Clause]
    summary: str = ""
    summary_source: Literal["llm", "rules"] = "rules"
    ollama: OllamaStatus
    warnings: List[str] = Field(default_factory=list)
