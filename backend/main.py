"""Doc Decode FastAPI app.

Uploads are held in memory for the length of one request and never written to
disk, so there is no stored copy to delete afterwards. Document text is not
logged (see LOG_DOCUMENT_TEXT in config).
"""
import logging
import threading
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

import ai_explainer
import calendar_export
import clause_detector
import comparison
import config
import demo_catalog
import document_classifier
import eligibility as tender_eligibility
import ocr_reader
import ollama_service
import pdf_reader
import pipeline
import question_answering
import tts_service
from schemas import (
    AnalysisResult,
    AskRequest,
    AskResponse,
    CalendarRequest,
    CompareRequest,
    CompareResponse,
    DemoDocument,
    EligibilityRequest,
    EligibilityResponse,
    ExplainRequest,
    ExplainResponse,
    ReclassifyRequest,
    ReclassifyResponse,
    TtsRequest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("doc_decode")

app = FastAPI(
    title="Doc Decode API",
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


@app.on_event("startup")
def preload_model() -> None:
    """Load the Ollama model in the background as the server starts.

    The server is usable immediately; this only means the first upload does not
    pay the cold model load. It never fails startup if Ollama is absent.
    """
    thread = threading.Thread(target=ollama_service.warm_up, daemon=True)
    thread.start()


@app.get("/api/health")
def health() -> dict:
    status = ollama_service.check_status(force=True)
    malayalam_model = config.model_for("ml")
    malayalam_status = (
        status
        if malayalam_model == config.OLLAMA_MODEL
        else ollama_service.check_status(force=True, model=malayalam_model)
    )
    ocr_ok, ocr_message = ocr_reader.ocr_status()
    tts_ok, tts_message, tts_languages = tts_service.tts_status()
    return {
        "status": "ok",
        "backend": "running",
        "ollama": status.model_dump(),
        "ollama_malayalam": malayalam_status.model_dump(),
        "ocr": {
            "available": ocr_ok,
            "message": ocr_message,
            "languages": list(ocr_reader.available_languages()),
            "active_languages": ocr_reader.resolve_langs() if ocr_ok else "",
            "malayalam": "mal" in ocr_reader.available_languages(),
        },
        "tts": {
            "available": tts_ok,
            "message": tts_message,
            "languages": tts_languages,
            "malayalam": tts_service.language_supported("ml"),
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
    status = ollama_service.check_status(
        force=True, model=config.model_for(request.language)
    )
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
        ics = calendar_export.build_ics(
            request.filename, request.deadlines, request.reminder_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date: %s" % exc) from exc
    name = calendar_export.safe_basename(request.filename.rsplit(".", 1)[0])
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="docdecode-%s.ics"' % name
        },
    )


@app.post("/api/tts")
def tts(request: TtsRequest) -> Response:
    """Speak text locally with eSpeak NG.

    Used only when the browser has no voice for the chosen language, which
    on Windows is the normal case for Malayalam. Nothing leaves the machine.
    """
    try:
        audio = tts_service.synthesize(request.text, request.language)
    except tts_service.TtsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/reclassify", response_model=ReclassifyResponse)
def reclassify(request: ReclassifyRequest) -> ReclassifyResponse:
    """Re-run the structured pipeline under a type the user picked. Takes the
    text the first analysis already produced, so no file is re-uploaded."""
    if request.doc_type != "other" and request.doc_type not in document_classifier.RULES:
        raise HTTPException(status_code=400, detail="Unknown document type: %s" % request.doc_type)
    language = request.language if request.language in ("en", "ml") else "en"
    return pipeline.reclassify(
        doc_type=request.doc_type,
        pages=request.pages,
        language=language,
        filename=request.filename,
    )


@app.post("/api/compare", response_model=CompareResponse)
def compare(request: CompareRequest) -> CompareResponse:
    """Compare an invoice with a purchase order, from the facts and items already read."""
    return comparison.compare(request.left, request.right)


@app.post("/api/eligibility", response_model=EligibilityResponse)
def eligibility(request: EligibilityRequest) -> EligibilityResponse:
    """A checklist of the tender's requirements against what the user entered.
    It never says the user is or is not eligible."""
    return tender_eligibility.check(request)


@app.get("/api/demo", response_model=List[DemoDocument])
def demo_list() -> List[DemoDocument]:
    return demo_catalog.list_documents()


@app.get("/api/demo/{demo_id}/file")
def demo_file(demo_id: str) -> Response:
    """Serve an allowlisted demo PDF. The client sends an id, never a path."""
    data = demo_catalog.file_bytes(demo_id)
    name = demo_catalog.filename_for(demo_id)
    if data is None or name is None:
        raise HTTPException(status_code=404, detail="Unknown demo document.")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="%s"' % name,
            "Cache-Control": "no-store",
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
