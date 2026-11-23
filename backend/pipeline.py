"""Upload validation and the end-to-end analysis pipeline."""
import logging
import time
import uuid
from typing import List, Optional, Tuple

import ai_explainer
import clause_detector
import config
import deadline_extractor
import doc_intel
import document_classifier
import fact_extractor
import findings as finding_builder
import line_items as item_reader
import money
import ollama_service
import pdf_reader
import verification as verifier
from schemas import (
    ActionItem,
    AnalysisResult,
    Clause,
    Deadline,
    Fact,
    Finding,
    Language,
    LineItem,
    PageText,
    ReclassifyResponse,
    Segment,
    TenderRequirement,
    VerificationReport,
)
from utils import build_segments

# Types that carry a line-item table worth reading.
ITEM_TYPES = {"invoice", "purchase_order"}

logger = logging.getLogger(__name__)

# Magic bytes, so a renamed .exe cannot pass as a PDF.
SIGNATURES = (
    (b"%PDF-", "pdf"),
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
)


class UploadRejected(ValueError):
    """The upload failed validation."""


def _extension(filename: str) -> str:
    name = (filename or "").lower().strip()
    dot = name.rfind(".")
    return name[dot:] if dot != -1 else ""


def sniff_kind(data: bytes) -> Optional[str]:
    for signature, kind in SIGNATURES:
        if data.startswith(signature):
            return kind
    return None


def validate_upload(filename: str, content_type: str, data: bytes) -> str:
    """Return "pdf" or "image". Raise UploadRejected with a readable reason."""
    if not data:
        raise UploadRejected("The uploaded file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise UploadRejected(
            "This file is %.1f MB. The limit is %d MB (MAX_UPLOAD_MB in .env)."
            % (len(data) / (1024 * 1024), config.MAX_UPLOAD_MB)
        )

    extension = _extension(filename)
    if extension not in config.ALLOWED_EXTENSIONS:
        raise UploadRejected(
            "Only PDF, JPG, JPEG and PNG files are accepted. Got: %s"
            % (extension or "no extension")
        )

    declared = (content_type or "").split(";")[0].strip().lower()
    if declared and declared not in config.ALLOWED_MIME_TYPES:
        raise UploadRejected("Unsupported content type: %s" % declared)

    # Content decides, not the filename.
    kind = sniff_kind(data)
    if kind is None:
        raise UploadRejected(
            "The file contents are not a readable PDF or image, whatever the file "
            "name says."
        )
    if kind == "pdf" and extension != ".pdf":
        raise UploadRejected("This file is a PDF but is named %s." % extension)
    if kind != "pdf" and extension == ".pdf":
        raise UploadRejected("This file is named .pdf but its contents are an image.")
    return "pdf" if kind == "pdf" else "image"


def analyse(
    filename: str,
    content_type: str,
    data: bytes,
    language: Language = "en",
    use_ai: bool = True,
) -> AnalysisResult:
    """Validate, extract, classify, detect, then explain. One LLM round-trip."""
    started = time.monotonic()
    kind = validate_upload(filename, content_type, data)
    size = len(data)

    if kind == "pdf":
        pages, info = pdf_reader.extract_pdf(data)
    else:
        pages, info = pdf_reader.extract_image(data)

    full_text = "\n\n".join(p.text for p in pages if p.text.strip())
    segments = build_segments((p.page, p.text) for p in pages)
    warnings: List[str] = list(info["warnings"])

    stages: List[str] = ["Text read (%s)" % ", ".join(sorted({p.source for p in pages}))]
    classification = document_classifier.classify(full_text)
    stages.append("Document type classified")
    facts = fact_extractor.extract_facts(segments, classification.doc_type)
    clauses = clause_detector.detect_clauses(segments, classification.doc_type)
    deadlines = deadline_extractor.extract_deadlines(segments)
    stages += ["Facts extracted", "Clauses detected", "Deadlines found"]

    (
        facts, line_items, requirements, verification, findings, actions, type_stages,
    ) = _type_specific(classification.doc_type, pages, facts, clauses, deadlines)
    stages += type_stages

    doc_label = classification.label if classification.certain else "unknown / uncertain"

    status = ollama_service.check_status(model=config.model_for(language))
    summary = ai_explainer.rule_summary(doc_label, facts, clauses)
    summary_source = "rules"

    if use_ai and clauses and status.reachable and status.model_available:
        clauses, clause_warnings = ai_explainer.explain_clauses(
            clauses, doc_label, facts, language
        )
        warnings.extend(clause_warnings)
        summary, summary_source, summary_warnings = ai_explainer.build_summary(
            doc_label, facts, clauses, language
        )
        warnings.extend(summary_warnings)
    else:
        if not use_ai:
            warnings.append("AI explanations were switched off for this analysis.")
        elif not (status.reachable and status.model_available):
            warnings.append(status.message)
        for clause in clauses:
            clause.explanation = _rule_only_explanation(clause, language)

    if not full_text.strip():
        warnings.append(
            "Nothing could be analysed because no text was extracted from the file."
        )
    stages.append("Explanations written" if summary_source == "llm" else "Rule explanations written")

    logger.info(
        "analysed %s (%s, %d pages, %d chars, %d clauses) in %dms",
        filename,
        classification.doc_type,
        len(pages),
        len(full_text),
        len(clauses),
        int((time.monotonic() - started) * 1000),
    )

    return AnalysisResult(
        analysis_id=uuid.uuid4().hex[:12],
        filename=filename,
        file_size_bytes=size,
        page_count=info.get("total_pages") or len(pages),
        classification=classification,
        language=language,
        doc_type_options=document_classifier.options(),
        extraction_sources=sorted({p.source for p in pages}),
        ocr_used=info["ocr_used"],
        ocr_available=info["ocr_available"],
        ocr_message=info["ocr_message"],
        text_chars=len(full_text),
        facts=facts,
        clauses=clauses,
        deadlines=deadlines,
        line_items=line_items,
        verification=verification,
        findings=findings,
        actions=actions,
        requirements=requirements,
        segments=segments,
        pages=pages,
        summary=summary,
        summary_source=summary_source,
        ollama=status,
        warnings=_dedupe(warnings),
        attention_counts=clause_detector.attention_counts(clauses),
        duration_ms=int((time.monotonic() - started) * 1000),
        stages=stages,
    )


def _type_specific(
    doc_type: str,
    pages: List[PageText],
    facts: List[Fact],
    clauses: List[Clause],
    deadlines: List[Deadline],
) -> Tuple[
    List[Fact], List[LineItem], List[TenderRequirement], VerificationReport,
    List[Finding], List[ActionItem], List[str],
]:
    """The structured-document half of the pipeline, shared by analyse and reclassify.

    Fields the type expects are added to the generic facts only where the
    generic extractor did not already produce that key.
    """
    stages: List[str] = []
    seen = {fact.key for fact in facts}
    merged = list(facts)
    for fact in doc_intel.fields(doc_type, pages):
        if fact.key not in seen:
            seen.add(fact.key)
            merged.append(fact)
    if doc_type in doc_intel.SPECS:
        stages.append("Labelled fields read")

    line_items: List[LineItem] = []
    if doc_type in ITEM_TYPES:
        line_items = item_reader.extract(doc_intel.item_source(pages))
        stages.append("Line items read")

    requirements: List[TenderRequirement] = []
    if doc_type == "tender":
        requirements = doc_intel.tender_requirements(pages)
        stages.append("Tender requirements read")

    currency = money.detect_currency("\n".join(p.text for p in pages))
    ocr = any(p.source == "ocr" for p in pages)
    report = verifier.verify(doc_type, merged, line_items, currency, ocr)
    if report.applicable:
        stages.append("Arithmetic verified")

    found, actions = finding_builder.build(doc_type, merged, deadlines, clauses, report)
    stages.append("Findings and actions built")
    return merged, line_items, requirements, report, found, actions, stages


def reclassify(
    doc_type: str,
    pages: List[PageText],
    language: Language = "en",
    filename: str = "document",
) -> ReclassifyResponse:
    """Re-run the pipeline under a type the user chose, from text already extracted.

    No file is needed and no OCR runs again. Explanations are rule-based here;
    the AI step belongs to a fresh analysis.
    """
    full_text = "\n\n".join(p.text for p in pages if p.text.strip())
    segments: List[Segment] = build_segments((p.page, p.text) for p in pages)
    classification = document_classifier.forced(doc_type, full_text)
    facts = fact_extractor.extract_facts(segments, doc_type)
    clauses = clause_detector.detect_clauses(segments, doc_type)
    deadlines = deadline_extractor.extract_deadlines(segments)
    for clause in clauses:
        clause.explanation = _rule_only_explanation(clause, language)

    facts, line_items, requirements, report, findings, actions, _stages = _type_specific(
        doc_type, pages, facts, clauses, deadlines
    )
    return ReclassifyResponse(
        classification=classification,
        facts=facts,
        clauses=clauses,
        deadlines=deadlines,
        line_items=line_items,
        verification=report,
        findings=findings,
        actions=actions,
        requirements=requirements,
        attention_counts=clause_detector.attention_counts(clauses),
        warnings=["Re-run under the type you chose. Explanations are rule-based."],
    )


def _rule_only_explanation(clause, language: str):
    from schemas import ClauseExplanation

    return ClauseExplanation(
        **clause_detector.rule_explanation(clause, language),
        source="rules",
        language=language,
    )


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
