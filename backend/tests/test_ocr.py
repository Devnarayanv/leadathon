"""Real OCR tests.

These need Tesseract installed and are skipped when it is not, so the suite
still passes on a machine without it. A scanned PDF is built on the fly by
rendering the demo agreement to images, which gives a page with no text layer
exactly like a real scan.
"""
import pytest
import pymupdf

import ocr_reader
import pdf_reader
import pipeline

tesseract_available = ocr_reader.ocr_status()[0]
needs_tesseract = pytest.mark.skipif(
    not tesseract_available, reason="Tesseract OCR is not installed on this machine"
)


@pytest.fixture(scope="module")
def scanned_pdf_bytes(request):
    """The demo rental agreement rendered to images: no text layer at all."""
    source_path = request.path.parent.parent.parent / "demo" / "demo_rental_agreement.pdf"
    source = pymupdf.open(str(source_path))
    out = pymupdf.open()
    try:
        for index in range(source.page_count):
            page = source.load_page(index)
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=pixmap.tobytes("png"))
        return out.tobytes()
    finally:
        out.close()
        source.close()


@pytest.fixture(scope="module")
def page_photo_bytes(request):
    source_path = request.path.parent.parent.parent / "demo" / "demo_rental_agreement.pdf"
    source = pymupdf.open(str(source_path))
    try:
        return source.load_page(0).get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")
    finally:
        source.close()


def test_a_scanned_pdf_really_has_no_text_layer(scanned_pdf_bytes):
    doc = pymupdf.open(stream=scanned_pdf_bytes, filetype="pdf")
    try:
        assert doc.page_count == 2
        for index in range(doc.page_count):
            assert doc.load_page(index).get_text("text").strip() == ""
    finally:
        doc.close()


@needs_tesseract
def test_ocr_fallback_reads_a_scanned_pdf(scanned_pdf_bytes):
    pages, info = pdf_reader.extract_pdf(scanned_pdf_bytes)
    assert info["ocr_used"] is True
    assert info["ocr_pages"] == [1, 2]
    assert all(page.source == "ocr" for page in pages)
    text = "\n".join(page.text for page in pages)
    assert "18,500" in text
    assert "security deposit" in text.lower()


@needs_tesseract
def test_scanned_document_produces_the_same_key_facts(scanned_pdf_bytes):
    result = pipeline.analyse(
        "scan.pdf", "application/pdf", scanned_pdf_bytes, use_ai=False
    )
    assert result.ocr_used is True
    assert result.classification.doc_type == "rental_agreement"
    values = {fact.key: fact.value for fact in result.facts}
    assert values["rent"] == "Rs. 18,500"
    assert values["deposit"] == "Rs. 1,10,000"
    assert values["end_date"] == "28th February 2026"
    assert result.clauses


@needs_tesseract
def test_photo_upload_is_ocred_as_a_single_page(page_photo_bytes):
    result = pipeline.analyse("photo.png", "image/png", page_photo_bytes, use_ai=False)
    assert result.ocr_used is True
    assert result.page_count == 1
    assert result.pages[0].source == "ocr"
    assert result.text_chars > 500
    assert result.classification.doc_type == "rental_agreement"


@needs_tesseract
def test_ocr_page_budget_is_respected(scanned_pdf_bytes, monkeypatch):
    import config

    monkeypatch.setattr(config, "OCR_MAX_PAGES", 1)
    pages, info = pdf_reader.extract_pdf(scanned_pdf_bytes)
    assert info["ocr_pages"] == [1]
    assert pages[1].source == "empty"
    assert any("OCR ran on 1 of 2" in warning for warning in info["warnings"])


@needs_tesseract
def test_unreadable_image_is_reported_not_crashed():
    with pytest.raises(ValueError):
        ocr_reader.ocr_image_bytes(b"this is not an image at all")


@needs_tesseract
def test_blank_image_reports_that_nothing_was_read():
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (900, 600), "white").save(buffer, format="PNG")
    result = pipeline.analyse(
        "blank.png", "image/png", buffer.getvalue(), use_ai=False
    )
    assert result.text_chars == 0
    assert result.facts == []
    assert any("read no text" in warning for warning in result.warnings)


def test_requested_languages_are_filtered_to_what_is_installed(monkeypatch):
    import config

    monkeypatch.setattr(config, "OCR_LANGS", "eng+mal+klingon")
    resolved = ocr_reader.resolve_langs()
    installed = ocr_reader.available_languages()
    if installed:
        # A language pack that is not installed must never be passed to Tesseract.
        for part in resolved.split("+"):
            assert part in installed
    else:
        assert resolved == "eng"
