"""API surface: health, analyze, ask, explain, calendar, and bad input."""
import calendar_export
from schemas import CalendarDeadline


def test_health_reports_real_state(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["ollama"]) >= {"reachable", "model", "model_available", "base_url"}
    assert body["limits"]["max_upload_mb"] > 0
    assert ".pdf" in body["accepted_types"]
    # The badge must never show a model as ready unless the server is reachable.
    if not body["ollama"]["reachable"]:
        assert body["ollama"]["model_available"] is False
        assert body["ollama"]["message"]


def test_analyze_returns_a_full_structured_result(client, rental_pdf_bytes):
    response = client.post(
        "/api/analyze",
        files={"file": ("demo_rental_agreement.pdf", rental_pdf_bytes, "application/pdf")},
        data={"language": "en", "use_ai": "false"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["doc_type"] == "rental_agreement"
    assert body["page_count"] == 2
    assert body["facts"] and body["clauses"] and body["segments"] and body["pages"]
    assert body["attention_counts"]
    assert body["duration_ms"] >= 0
    # Every clause must carry its original text and an explanation of some kind.
    for clause in body["clauses"]:
        assert clause["text"]
        assert clause["explanation"]["source"] in ("llm", "rules")


def test_analyze_rejects_a_non_document(client):
    response = client.post(
        "/api/analyze",
        files={"file": ("evil.pdf", b"MZ\x90\x00 this is an executable", "application/pdf")},
    )
    assert response.status_code == 400
    assert "not a readable PDF" in response.json()["detail"]


def test_analyze_rejects_an_unsupported_extension(client):
    response = client.post(
        "/api/analyze",
        files={"file": ("notes.txt", b"just some text here", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF, JPG" in response.json()["detail"]


def test_analyze_rejects_an_empty_file(client):
    response = client.post(
        "/api/analyze", files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_analyze_rejects_an_oversized_file(client, monkeypatch):
    import config

    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10)
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 1)
    response = client.post(
        "/api/analyze",
        files={"file": ("big.pdf", b"%PDF-" + b"0" * 500, "application/pdf")},
    )
    assert response.status_code == 400
    assert "limit is 1 MB" in response.json()["detail"]


def test_analyze_handles_a_corrupt_pdf(client):
    response = client.post(
        "/api/analyze",
        files={"file": ("broken.pdf", b"%PDF-1.4 truncated nonsense", "application/pdf")},
    )
    assert response.status_code == 422
    assert "could not be opened" in response.json()["detail"]


def test_image_upload_without_ocr_reports_it_rather_than_failing(client, monkeypatch):
    import ocr_reader

    # pdf_reader calls ocr_reader.ocr_status() through the module, so patching
    # the module attribute covers both call sites.
    monkeypatch.setattr(
        ocr_reader, "ocr_status", lambda: (False, "Tesseract OCR was not found.")
    )
    # A 1x1 PNG.
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082"
    )
    response = client.post(
        "/api/analyze", files={"file": ("scan.png", png, "image/png")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ocr_available"] is False
    assert any("OCR" in warning for warning in body["warnings"])
    assert body["facts"] == []


def test_ask_requires_document_text(client):
    response = client.post(
        "/api/ask", json={"question": "What is the rent?", "segments": []}
    )
    assert response.status_code == 400


def test_ask_rejects_an_empty_question(client):
    response = client.post(
        "/api/ask",
        json={"question": "", "segments": [{"id": 1, "text": "The rent is Rs. 500.", "page": 1}]},
    )
    assert response.status_code == 422


def test_ask_answers_from_supplied_segments(client, rental_pdf_bytes):
    analysis = client.post(
        "/api/analyze",
        files={"file": ("rent.pdf", rental_pdf_bytes, "application/pdf")},
        data={"use_ai": "false"},
    ).json()
    response = client.post(
        "/api/ask",
        json={
            "question": "What is the notice period?",
            "segments": analysis["segments"],
            "doc_type": "rental_agreement",
            "language": "en",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["evidence"]
    assert any("notice" in item["text"].lower() for item in body["evidence"])


def test_explain_re_explains_without_a_re_upload(client, rental_pdf_bytes, ollama_down):
    # ollama_down keeps this deterministic and fast. With a real server the
    # Malayalam path would load the large OLLAMA_MODEL_ML model, turning a unit
    # test into a multi-minute generation.
    analysis = client.post(
        "/api/analyze",
        files={"file": ("rent.pdf", rental_pdf_bytes, "application/pdf")},
        data={"use_ai": "false"},
    ).json()
    response = client.post(
        "/api/explain",
        json={
            "doc_type": "rental_agreement",
            "language": "ml",
            "clauses": analysis["clauses"][:3],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["clauses"]) == 3
    assert all(
        clause["explanation"]["language"] == "ml" for clause in body["clauses"]
    )


def test_calendar_returns_a_valid_ics_attachment(client):
    response = client.post(
        "/api/calendar",
        json={
            "filename": "demo_rental_agreement.pdf",
            "deadlines": [
                {
                    "date_iso": "2026-02-28",
                    "description": "Agreement expiry",
                    "source_text": "expires on 28th February 2026",
                    "page": 1,
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert ".ics" in response.headers["content-disposition"]
    body = response.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert body.rstrip().endswith("END:VCALENDAR")
    assert "DTSTART;VALUE=DATE:20260228" in body
    # All-day events end on the following day.
    assert "DTEND;VALUE=DATE:20260301" in body


def test_calendar_rejects_a_bad_date(client):
    response = client.post(
        "/api/calendar",
        json={"filename": "x.pdf", "deadlines": [{"date_iso": "nope", "description": "d"}]},
    )
    assert response.status_code == 400


def test_calendar_requires_at_least_one_deadline(client):
    response = client.post("/api/calendar", json={"filename": "x.pdf", "deadlines": []})
    assert response.status_code == 422


def test_ics_escapes_commas_and_semicolons():
    ics = calendar_export.build_ics(
        "doc.pdf",
        [
            CalendarDeadline(
                date_iso="2025-07-15",
                description="Pay Rs. 1,000; or reply",
                source_text="line one\nline two",
            )
        ],
    )
    assert "Rs. 1\\,000\\; or reply" in ics
    # Long lines are folded with CRLF + a space, so unfold before checking the
    # escaped payload. No content line may exceed 75 octets.
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, line
    unfolded = ics.replace("\r\n ", "")
    assert "line one\\nline two" in unfolded


def test_rules_endpoint_lists_what_the_engine_checks(client):
    response = client.get("/api/rules")
    assert response.status_code == 200
    body = response.json()
    assert len(body["document_types"]) >= 4
    assert len(body["clause_categories"]) >= 12
    for category in body["clause_categories"]:
        assert category["phrase_count"] > 0
        assert category["suggested_action"]


# ---------------------------------------------------------------- reminders


def test_calendar_reminder_lead_time_is_honoured(client):
    for days, trigger in ((0, "TRIGGER:-PT0M"), (1, "TRIGGER:-P1D"), (14, "TRIGGER:-P14D")):
        response = client.post(
            "/api/calendar",
            json={
                "filename": "x.pdf",
                "reminder_days": days,
                "deadlines": [{"date_iso": "2026-02-28", "description": "Expiry"}],
            },
        )
        assert response.status_code == 200
        assert trigger in response.text, days


def test_calendar_defaults_to_a_three_day_reminder(client):
    response = client.post(
        "/api/calendar",
        json={
            "filename": "x.pdf",
            "deadlines": [{"date_iso": "2026-02-28", "description": "Expiry"}],
        },
    )
    assert "TRIGGER:-P3D" in response.text


def test_calendar_rejects_an_absurd_reminder_lead_time(client):
    response = client.post(
        "/api/calendar",
        json={
            "filename": "x.pdf",
            "reminder_days": 900,
            "deadlines": [{"date_iso": "2026-02-28", "description": "Expiry"}],
        },
    )
    assert response.status_code == 422


def test_every_event_still_carries_one_alarm(client):
    response = client.post(
        "/api/calendar",
        json={
            "filename": "x.pdf",
            "reminder_days": 7,
            "deadlines": [
                {"date_iso": "2026-02-28", "description": "Expiry"},
                {"date_iso": "2026-03-15", "description": "Payment due"},
            ],
        },
    )
    body = response.text
    assert body.count("BEGIN:VEVENT") == 2
    assert body.count("BEGIN:VALARM") == 2
    assert body.count("TRIGGER:-P7D") == 2


# ---------------------------------------------------------------- speech


def test_health_reports_speech_engine_state(client):
    body = client.get("/api/health").json()
    assert "tts" in body
    assert set(body["tts"]) >= {"available", "message", "languages", "malayalam"}
    # It must never claim Malayalam speech it cannot deliver.
    if not body["tts"]["available"]:
        assert body["tts"]["malayalam"] is False
        assert body["tts"]["message"]


def test_tts_without_the_engine_returns_503_not_silence(client, monkeypatch):
    import tts_service

    monkeypatch.setattr(
        tts_service,
        "synthesize",
        lambda *a, **k: (_ for _ in ()).throw(
            tts_service.TtsUnavailable("eSpeak NG is not installed.")
        ),
    )
    response = client.post("/api/tts", json={"text": "hello", "language": "en"})
    assert response.status_code == 503
    assert "not installed" in response.json()["detail"]


def test_tts_rejects_empty_text(client):
    response = client.post("/api/tts", json={"text": "", "language": "en"})
    assert response.status_code == 422


def test_tts_rejects_oversized_text(client):
    response = client.post("/api/tts", json={"text": "x" * 5000, "language": "en"})
    assert response.status_code == 422


def test_tts_returns_wav_audio_when_the_engine_is_present(client, monkeypatch):
    import tts_service

    fake_wav = b"RIFF\x24\x00\x00\x00WAVEfmt "
    monkeypatch.setattr(tts_service, "synthesize", lambda text, language="en": fake_wav)
    response = client.post(
        "/api/tts", json={"text": "വാടക", "language": "ml"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content.startswith(b"RIFF")


def test_tts_passes_the_requested_language_through(client, monkeypatch):
    import tts_service

    seen = {}

    def fake(text, language="en"):
        seen["language"] = language
        seen["text"] = text
        return b"RIFF"

    monkeypatch.setattr(tts_service, "synthesize", fake)
    client.post("/api/tts", json={"text": "hello there", "language": "ml"})
    assert seen["language"] == "ml"
