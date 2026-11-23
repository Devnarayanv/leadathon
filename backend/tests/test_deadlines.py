"""Deadlines that used to be dropped: monthly obligations and notice windows."""
import deadline_extractor
from schemas import Segment


def _extract(*sentences):
    segments = [Segment(id=i + 1, text=s, page=1) for i, s in enumerate(sentences)]
    return deadline_extractor.extract_deadlines(segments)


def test_recurring_monthly_deadline_is_kept_without_inventing_a_date():
    items = _extract(
        "3. RENT The Tenant shall pay a monthly rent of Rs. 18,500/- on or before "
        "the 5th day of every English calendar month."
    )
    recurring = [d for d in items if d.recurrence]
    assert len(recurring) == 1
    assert recurring[0].date_iso is None
    assert recurring[0].recurrence == "monthly, day 5"
    assert recurring[0].needs_verification is True
    assert recurring[0].date_text == "5th day of every English calendar month"


def test_days_before_a_stated_date_is_calculated_and_flagged():
    items = _extract(
        "Unless either party gives written notice of its intention not to continue "
        "at least 30 days before 28th February 2026, this agreement shall stand renewed."
    )
    calculated = [d for d in items if d.evidence_status == "calculated"]
    assert len(calculated) == 1
    assert calculated[0].date_iso == "2026-01-29"
    assert calculated[0].needs_verification is True
    assert "30 days before 28th February 2026" in calculated[0].description


def test_plain_expiry_still_extracted_once():
    items = _extract(
        "The agreement is for 11 months and expires on 28th February 2026."
    )
    assert [d.date_iso for d in items] == ["2026-02-28"]
    assert items[0].evidence_status == "extracted"


def test_tender_bid_opening_date_becomes_a_deadline():
    items = _extract("Bid opening date: 17/12/2026")
    dated = [d for d in items if d.date_iso == "2026-12-17"]
    assert len(dated) == 1
    assert "opening" in dated[0].description.lower()
