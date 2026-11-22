"""Pydantic models for API requests, responses and validated LLM output."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Language = Literal["en", "ml"]

# How a value on screen came to exist. Shown next to every figure so the user
# can tell a quoted number from one Doc Decode worked out or a model guessed.
EvidenceStatus = Literal["extracted", "calculated", "interpreted", "needs_verification"]

VerificationStatus = Literal[
    "verified",
    "needs_attention",
    "mismatch",
    "missing_information",
    "unable_to_verify",
]


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
    evidence_status: EvidenceStatus = "extracted"


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
    """A date the document ties to an action.

    `date_text` is always the document's own wording. `date_iso` is present
    only when that wording could be resolved to one calendar day with no
    guessing; when it could not, the wording stands on its own and the item is
    marked needs_verification rather than being silently normalised.
    """

    id: int
    title: str = ""
    deadline_type: str = "other"
    date_iso: Optional[str] = None
    date_text: str
    time_text: Optional[str] = None
    description: str
    source_text: str
    page: Optional[int] = None
    confidence: Literal["high", "medium", "low"]
    evidence_status: EvidenceStatus = "extracted"
    needs_verification: bool = False
    recurrence: Optional[str] = None
    verified: bool = False
    origin: Literal["cue", "field", "table"] = "cue"


class LineItem(BaseModel):
    description: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[str] = None
    amount: Optional[str] = None
    amount_was_computed: bool = False
    page: Optional[int] = None
    source_text: Optional[str] = None


class VerificationCheck(BaseModel):
    """One arithmetic check, with everything needed to re-do it by hand."""

    key: str
    label: str
    status: VerificationStatus
    formula: str = ""
    inputs: List[Dict[str, str]] = Field(default_factory=list)
    document_value: Optional[str] = None
    calculated_value: Optional[str] = None
    difference: Optional[str] = None
    explanation: str = ""
    page: Optional[int] = None
    source_text: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    applicable: bool = False
    kind: str = "none"
    kind_label: str = ""
    status: VerificationStatus = "unable_to_verify"
    headline: str = ""
    checks: List[VerificationCheck] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)


class Finding(BaseModel):
    """An evidence-first observation. Every field is traceable to the file."""

    id: int
    title: str
    category: Literal[
        "deadline",
        "financial_obligation",
        "important_condition",
        "verification_required",
        "missing_information",
    ]
    severity: Literal["high", "medium", "low"] = "medium"
    evidence_status: EvidenceStatus = "extracted"
    original_text: str = ""
    page: Optional[int] = None
    explanation: str = ""
    why_it_matters: str = ""
    suggested_action: str = ""
    confidence: Literal["high", "medium", "low"] = "medium"
    ref: str = ""


class ActionItem(BaseModel):
    id: int
    title: str
    detail: str = ""
    due_date_iso: Optional[str] = None
    due_date_text: Optional[str] = None
    page: Optional[int] = None
    source_text: str = ""
    finding_ref: str = ""
    priority: Literal["high", "medium", "low"] = "medium"


class TenderRequirement(BaseModel):
    label: str
    description: str = ""
    mandatory: Optional[bool] = None
    page: Optional[int] = None
    source_text: str = ""
    kind: Literal["eligibility", "document", "financial", "technical"] = "eligibility"


class Classification(BaseModel):
    doc_type: str
    label: str
    certain: bool
    score: int = 0
    matched_terms: List[str] = Field(default_factory=list)
    reason: str = ""
    runner_up: Optional[str] = None
    runner_up_label: Optional[str] = None
    user_set: bool = False


class DocTypeOption(BaseModel):
    key: str
    label: str


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
    doc_type_options: List[DocTypeOption] = Field(default_factory=list)
    language: Language = "en"
    extraction_sources: List[str] = Field(default_factory=list)
    ocr_used: bool = False
    ocr_available: bool = True
    ocr_message: str = ""
    text_chars: int = 0
    facts: List[Fact] = Field(default_factory=list)
    clauses: List[Clause] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    line_items: List[LineItem] = Field(default_factory=list)
    verification: VerificationReport = Field(default_factory=VerificationReport)
    findings: List[Finding] = Field(default_factory=list)
    actions: List[ActionItem] = Field(default_factory=list)
    requirements: List[TenderRequirement] = Field(default_factory=list)
    segments: List[Segment] = Field(default_factory=list)
    pages: List[PageText] = Field(default_factory=list)
    summary: str = ""
    summary_source: Literal["llm", "rules"] = "rules"
    ollama: OllamaStatus
    warnings: List[str] = Field(default_factory=list)
    attention_counts: dict = Field(default_factory=dict)
    duration_ms: int = 0
    stages: List[str] = Field(default_factory=list)


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


class ReclassifyRequest(BaseModel):
    """Re-run the type-specific half of the pipeline under a corrected type.

    The document text the user already uploaded is sent back rather than the
    file, so a correction costs no second upload and no second OCR pass.
    """

    doc_type: str
    language: Language = "en"
    filename: str = "document"
    pages: List[PageText] = Field(min_length=1, max_length=60)


class ReclassifyResponse(BaseModel):
    classification: Classification
    facts: List[Fact] = Field(default_factory=list)
    clauses: List[Clause] = Field(default_factory=list)
    deadlines: List[Deadline] = Field(default_factory=list)
    line_items: List[LineItem] = Field(default_factory=list)
    verification: VerificationReport = Field(default_factory=VerificationReport)
    findings: List[Finding] = Field(default_factory=list)
    actions: List[ActionItem] = Field(default_factory=list)
    requirements: List[TenderRequirement] = Field(default_factory=list)
    attention_counts: dict = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class ComparableDocument(BaseModel):
    analysis_id: str = ""
    filename: str = "document"
    doc_type: str = "other"
    facts: List[Fact] = Field(default_factory=list)
    line_items: List[LineItem] = Field(default_factory=list)


class CompareRequest(BaseModel):
    left: ComparableDocument
    right: ComparableDocument


class ComparisonRow(BaseModel):
    label: str
    left_value: Optional[str] = None
    right_value: Optional[str] = None
    result: Literal["match", "mismatch", "missing_left", "missing_right", "extra"]
    note: str = ""


class CompareResponse(BaseModel):
    comparable: bool
    kind: str = "none"
    headline: str = ""
    left_label: str = ""
    right_label: str = ""
    field_rows: List[ComparisonRow] = Field(default_factory=list)
    item_rows: List[ComparisonRow] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class DemoDocument(BaseModel):
    id: str
    label: str
    description: str
    doc_type: str
    filename: str
    size_bytes: int = 0
    highlight: str = ""


class EligibilityRequest(BaseModel):
    """What the user says about their business, checked against a tender's requirements."""

    business_type: str = Field(default="", max_length=120)
    # Typed as the user writes it, e.g. "Rs. 75,00,000" or "75 lakh". Parsed with money.parse.
    turnover: Optional[str] = Field(default=None, max_length=60)
    experience_years: Optional[float] = Field(default=None, ge=0, le=100)
    certifications: List[str] = Field(default_factory=list, max_length=30)
    registrations: List[str] = Field(default_factory=list, max_length=30)
    documents: List[str] = Field(default_factory=list, max_length=60)
    requirements: List[TenderRequirement] = Field(default_factory=list, max_length=60)


class EligibilityResponse(BaseModel):
    """Each row is {requirement, detail, page, source_text}. Never a guarantee of eligibility."""

    headline: str = ""
    meets: List[Dict[str, Optional[str]]] = Field(default_factory=list)
    does_not_meet: List[Dict[str, Optional[str]]] = Field(default_factory=list)
    missing: List[Dict[str, Optional[str]]] = Field(default_factory=list)
    needs_verification: List[Dict[str, Optional[str]]] = Field(default_factory=list)
    disclaimer: str = ""
