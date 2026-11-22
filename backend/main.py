"""PlainSpeak FastAPI app.

Uploads are held in memory for the length of one request and never written to
disk, so there is no stored copy to delete afterwards. Document text is not
logged (see LOG_DOCUMENT_TEXT in config).
"""
import logging
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

import ai_explainer
import calendar_export
import clause_detector
import config
import document_classifier
import ocr_reader
import ollama_service
import pdf_reader
import pipeline
import question_answering
from schemas import (
    AnalysisResult,
    AskRequest,
    AskResponse,
    CalendarRequest,
    ExplainRequest,
    ExplainResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("plainspeak")

app = FastAPI(
    title="PlainSpeak API",
    version="1.0.0",
    description="Local document understanding. Rule engine plus a local Ollama model.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(pipeline.UploadRejected)
async def upload_rejected_handler(_request: Request, exc: pipeline.UploadRejected):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(pdf_reader.UnreadableDocument)
async def unreadable_handler(_request: Request, exc: pdf_reader.UnreadableDocument):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict:
    status = ollama_service.check_status(force=True)
    ocr_ok, ocr_message = ocr_reader.ocr_status()
    return {
        "status": "ok",
        "backend": "running",
        "ollama": status.model_dump(),
        "ocr": {
            "available": ocr_ok,
            "message": ocr_message,
            "languages": list(ocr_reader.available_languages()),
            "active_languages": ocr_reader.resolve_langs() if ocr_ok else "",
            "malayalam": "mal" in ocr_reader.available_languages(),
        },
        "limits": {
            "max_upload_mb": config.MAX_UPLOAD_MB,
            "max_pages": config.MAX_PAGES,
            "ocr_max_pages": config.OCR_MAX_PAGES,
            "max_explained_clauses": config.MAX_EXPLAINED_CLAUSES,
        },
        "accepted_types": sorted(config.ALLOWED_EXTENSIONS),
    }


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze(
    file: UploadFile = File(...),
    language: str = Form("en"),
    use_ai: bool = Form(True),
) -> AnalysisResult:
    language = language if language in ("en", "ml") else "en"
    data = await file.read()
    try:
        return pipeline.analyse(
            filename=file.filename or "document",
            content_type=file.content_type or "",
            data=data,
            language=language,
            use_ai=use_ai,
        )
    finally:
        # Nothing is persisted; drop the bytes as soon as the request ends.
        del data
        await file.close()


@app.post("/api/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest) -> ExplainResponse:
    """Re-explain known clauses: used for language switching and for retrying
    after Ollama has been started. Avoids re-uploading the document."""
    status = ollama_service.check_status(force=True)
    doc_label = document_classifier.RULES.get(request.doc_type, {}).get(
        "label", "unknown / uncertain"
    )
    if not (status.reachable and status.model_available):
        clauses = list(request.clauses)
        for clause in clauses:
            clause.explanation = pipeline._rule_only_explanation(clause, request.language)
        return ExplainResponse(
            clauses=clauses,
            summary=ai_explainer.rule_summary(doc_label, [], clauses),
            summary_source="rules",
            ollama=status,
            warnings=[status.message],
        )

    clauses, warnings = ai_explainer.explain_clauses(
        list(request.clauses), doc_label, [], request.language
    )
    summary, summary_source, summary_warnings = ai_explainer.build_summary(
        doc_label, [], clauses, request.language
    )
    return ExplainResponse(
        clauses=clauses,
        summary=summary,
        summary_source=summary_source,
        ollama=status,
        warnings=pipeline._dedupe(warnings + summary_warnings),
    )


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    if not request.segments:
        raise HTTPException(
            status_code=400,
            detail="No document text was supplied. Analyse a document first.",
        )
    doc_label = document_classifier.RULES.get(request.doc_type, {}).get(
        "label", "unknown / uncertain"
    )
    return question_answering.answer_question(
        question=request.question,
        segments=request.segments,
        doc_type_label=doc_label,
        language=request.language,
    )


@app.post("/api/calendar")
def calendar(request: CalendarRequest) -> Response:
    try:
        ics = calendar_export.build_ics(request.filename, request.deadlines)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date: %s" % exc) from exc
    name = calendar_export.safe_basename(request.filename.rsplit(".", 1)[0])
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="plainspeak-%s.ics"' % name
        },
    )


@app.get("/api/rules")
def rules() -> dict:
    """What the rule engine actually looks for. Useful when demonstrating that
    the detections are deterministic rather than model guesses."""
    return {
        "document_types": [
            {"key": key, "label": rule["label"], "term_count": len(rule["terms"])}
            for key, rule in document_classifier.RULES.items()
        ],
        "clause_categories": [
            {
                "category": rule["category"],
                "label": rule["label"],
                "attention_level": rule["attention_level"],
                "attention_label": clause_detector.level_label(rule["attention_level"]),
                "phrase_count": len(rule["primary"]),
                "suggested_action": rule["action"],
            }
            for rule in clause_detector.RULES
        ],
    }
