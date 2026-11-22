"""Text extraction, cleanup and segmentation."""
import pytest

import pdf_reader
import utils


def test_pdf_text_extraction_reads_every_page(rental_pdf_bytes):
    pages, info = pdf_reader.extract_pdf(rental_pdf_bytes)
    assert len(pages) == 2
    assert info["total_pages"] == 2
    assert info["ocr_used"] is False
    assert all(page.source == "pdf_text" for page in pages)
    assert "security deposit" in pages[0].text.lower()


def test_extraction_preserves_amounts_and_dates(rental_pdf_bytes):
    pages, _info = pdf_reader.extract_pdf(rental_pdf_bytes)
    text = "\n".join(page.text for page in pages)
    assert "Rs. 18,500" in text
    assert "1,10,000" in text
    assert "28th February 2026" in text


def test_corrupt_pdf_raises_readable_error():
    with pytest.raises(pdf_reader.UnreadableDocument) as error:
        pdf_reader.extract_pdf(b"%PDF-1.4 this is not really a pdf")
    assert "could not be opened" in str(error.value)


def test_clean_text_rejoins_hyphen_breaks_but_keeps_sentences():
    cleaned = utils.clean_text("A security depos-\nit of Rs. 500.\nThe next sentence.")
    assert "deposit" in cleaned
    assert cleaned.count("\n") >= 1


def test_clean_text_keeps_paragraph_boundaries():
    cleaned = utils.clean_text("Clause one text.\n\n\n\nClause two text.")
    assert cleaned == "Clause one text.\n\nClause two text."


def test_split_sentences_does_not_break_on_rs_abbreviation():
    parts = utils.split_sentences("The rent is Rs. 15,000 per month. It is payable monthly.")
    assert len(parts) == 2
    assert "Rs. 15,000" in parts[0]


def test_split_sentences_starts_a_unit_at_numbered_clauses():
    parts = utils.split_sentences("1. First clause here.\n2. Second clause here.")
    assert len(parts) == 2


def test_segments_carry_page_numbers(rental_pdf_bytes):
    pages, _info = pdf_reader.extract_pdf(rental_pdf_bytes)
    segments = utils.build_segments((page.page, page.text) for page in pages)
    assert segments
    assert {segment.page for segment in segments} == {1, 2}
    assert all(segment.id > 0 for segment in segments)
    # Ids must be unique: the Q&A evidence links back through them.
    assert len({segment.id for segment in segments}) == len(segments)
