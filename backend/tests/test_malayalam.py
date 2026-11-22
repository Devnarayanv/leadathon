# -*- coding: utf-8 -*-
"""Malayalam document handling: script folding, amounts, durations and rules.

These cover the rule engine reading a Malayalam document. Whether the LLM can
*explain* in Malayalam is a separate matter, covered in test_ollama.py.
"""
import clause_detector
import dates
import document_classifier
import fact_extractor
import ocr_reader
import pytest
from schemas import Segment
from utils import fold_malayalam, normalise

CLEAN_LINES = [
    "ഈ വാടക കരാർ ഒരു മാതൃക രേഖയാണ്.",
    "പ്രതിമാസ വാടക 18,500 രൂപ ആയിരിക്കും.",
    "സെക്യൂരിറ്റി ഡിപ്പോസിറ്റ് 1,10,000 രൂപ നൽകിയിട്ടുണ്ട്.",
    "കരാർ കാലാവധി 11 മാസം ആണ്.",
    "നോട്ടീസ് കാലാവധി 2 മാസം ആയിരിക്കും.",
    "വൈകിയാൽ ദിവസം 250 രൂപ പിഴ ഈടാക്കും.",
    "ലോക്ക് ഇൻ കാലാവധി 6 മാസം ആയിരിക്കും.",
    "പലിശ നിരക്ക് 14.5% ആയിരിക്കും.",
]


def segs(*texts):
    return [Segment(id=i + 1, text=t, page=1) for i, t in enumerate(texts)]


def clean_segments():
    return segs(*CLEAN_LINES)


# ---------------------------------------------------------------- script folding


def test_both_chillu_encodings_fold_to_one_form():
    # Atomic chillu (ർ) and consonant + virama (ര്) are the same letter.
    atomic = "കരാർ കാലാവധി"
    decomposed = "കരാര് കാലാവധി"
    assert atomic != decomposed
    assert normalise(atomic) == normalise(decomposed)


def test_folding_leaves_english_and_digits_alone():
    assert fold_malayalam("Rs. 18,500 on 12/03/2025") == "Rs. 18,500 on 12/03/2025"


def test_keyword_written_with_chillu_matches_ocr_output():
    # OCR emits the decomposed form; the rules are written with chillu.
    detected = clause_detector.detect_clauses(
        segs("വൈകിയാല് ദിവസം 250 രൂപ പിഴ ഈടാക്കും എന്ന് കരാറില് പറയുന്നു.")
    )
    assert "penalty" in {clause.category for clause in detected}


# ---------------------------------------------------------------- amounts, durations


def test_malayalam_amount_suffix_is_read():
    assert dates.find_amount("പ്രതിമാസ വാടക 18,500 രൂപ ആണ്") == "18,500 രൂപ"
    assert dates.find_amount("ഡിപ്പോസിറ്റ് 1,10,000 രൂപ") == "1,10,000 രൂപ"


def test_malayalam_amount_keeps_its_own_unit_not_an_rs_prefix():
    value = dates.find_amount("250 രൂപ പിഴ")
    assert value is not None
    assert not value.startswith("Rs.")
    assert "രൂപ" in value


def test_a_bare_number_in_malayalam_is_not_money():
    assert dates.find_amount("കരാർ കാലാവധി 11 മാസം ആണ്") is None


def test_malayalam_durations():
    assert dates.find_duration(fold_malayalam("കരാർ കാലാവധി 11 മാസം")) == "11 മാസം"
    assert dates.duration_days(fold_malayalam("11 മാസം")) == 330
    assert dates.duration_days(fold_malayalam("15 ദിവസം")) == 15
    assert dates.duration_days(fold_malayalam("2 വർഷം")) == 730


def test_english_durations_still_win_when_both_appear():
    assert dates.duration_days("a period of 2 months") == 60


# ---------------------------------------------------------------- rules


def test_malayalam_rental_document_is_classified():
    result = document_classifier.classify("\n".join(CLEAN_LINES))
    assert result.doc_type == "rental_agreement"
    assert result.certain is True


def test_malayalam_facts_are_extracted():
    facts = fact_extractor.extract_facts(clean_segments(), "rental_agreement")
    values = {fact.key: fact.value for fact in facts}
    assert values["rent"] == "18,500 രൂപ"
    assert values["deposit"] == "1,10,000 രൂപ"
    assert values["duration"] == "11 മാസം"
    assert values["lock_in"] == "6 മാസം"
    assert values["penalty"] == "250 രൂപ"


def test_malayalam_clauses_are_detected():
    found = {
        clause.category
        for clause in clause_detector.detect_clauses(clean_segments(), "rental_agreement")
    }
    for category in ("penalty", "lock_in", "interest_rate", "notice_period"):
        assert category in found, category


def test_malayalam_facts_quote_the_document_unchanged():
    facts = fact_extractor.extract_facts(clean_segments(), "rental_agreement")
    rent = next(fact for fact in facts if fact.key == "rent")
    # source_text must be the document's own wording, never the folded copy.
    assert rent.source_text in CLEAN_LINES
    assert "ർ" in "".join(CLEAN_LINES)  # the originals do use atomic chillu


def test_malayalam_text_does_not_break_english_documents(rental_pdf_bytes):
    import pipeline

    result = pipeline.analyse(
        "rent.pdf", "application/pdf", rental_pdf_bytes, use_ai=False
    )
    values = {fact.key: fact.value for fact in result.facts}
    assert values["rent"] == "Rs. 18,500"
    assert result.classification.doc_type == "rental_agreement"


# ---------------------------------------------------------------- OCR language pack

malayalam_ocr = pytest.mark.skipif(
    "mal" not in ocr_reader.available_languages(),
    reason="Malayalam traineddata is not installed",
)


@malayalam_ocr
def test_malayalam_ocr_reads_a_rendered_notice(request):
    image_path = request.path.parent.parent.parent / "demo" / "demo_malayalam_notice.png"
    if not image_path.exists():
        pytest.skip("run demo/make_demo_docs.py first")
    text = ocr_reader.ocr_image_bytes(image_path.read_bytes())
    # Amounts survive OCR even where complex conjuncts do not.
    assert "18,500" in text
    assert "1,10,000" in text
    assert "250" in text
    assert "വാടക" in text


@malayalam_ocr
def test_malayalam_scan_produces_facts_end_to_end(request):
    import pipeline

    image_path = request.path.parent.parent.parent / "demo" / "demo_malayalam_notice.png"
    if not image_path.exists():
        pytest.skip("run demo/make_demo_docs.py first")
    result = pipeline.analyse(
        "ml.png", "image/png", image_path.read_bytes(), use_ai=False
    )
    assert result.ocr_used is True
    assert result.classification.doc_type == "rental_agreement"
    values = {fact.key: fact.value for fact in result.facts}
    assert "18,500" in values.get("rent", "")


def test_malayalam_is_dropped_when_the_pack_is_absent(monkeypatch):
    import config

    monkeypatch.setattr(config, "OCR_LANGS", "eng+mal")
    monkeypatch.setattr(ocr_reader, "available_languages", lambda: ("eng", "osd"))
    assert ocr_reader.resolve_langs() == "eng"


# ---------------------------------------------------------------- speech engine


def test_speech_engine_reports_absence_honestly():
    import tts_service

    ok, message, languages = tts_service.tts_status()
    if not ok:
        assert "eSpeak NG" in message
        assert languages == []
        assert tts_service.language_supported("ml") is False
    else:
        assert languages


def test_malayalam_maps_to_the_malayalam_voice():
    import tts_service

    assert tts_service.VOICE_BY_LANGUAGE["ml"] == "ml"
    assert tts_service.VOICE_BY_LANGUAGE["en"].startswith("en")


def test_synthesize_refuses_empty_text():
    import pytest as _pytest

    import tts_service

    if not tts_service.find_espeak():
        _pytest.skip("eSpeak NG is not installed")
    with _pytest.raises(ValueError):
        tts_service.synthesize("   ", "ml")
