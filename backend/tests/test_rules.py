"""Classification, fact extraction, clause detection, false positives, deadlines."""
import clause_detector
import dates
import deadline_extractor
import document_classifier
import fact_extractor
from schemas import Segment
from utils import build_segments


def segs(*texts):
    return [Segment(id=index + 1, text=text, page=1) for index, text in enumerate(texts)]


# ---------------------------------------------------------------- classification


def test_classifies_each_demo_document(
    rental_pdf_bytes, loan_pdf_bytes, bill_pdf_bytes, notice_pdf_bytes
):
    import pdf_reader

    expected = {
        "rental_agreement": rental_pdf_bytes,
        "loan_agreement": loan_pdf_bytes,
        "hospital_bill": bill_pdf_bytes,
        "government_notice": notice_pdf_bytes,
    }
    for doc_type, data in expected.items():
        pages, _info = pdf_reader.extract_pdf(data)
        text = "\n".join(page.text for page in pages)
        result = document_classifier.classify(text)
        assert result.doc_type == doc_type, doc_type
        assert result.certain is True


def test_empty_text_is_uncertain_not_guessed():
    result = document_classifier.classify("")
    assert result.doc_type == "other"
    assert result.certain is False
    assert "uncertain" in result.label.lower()


def test_unrelated_text_is_not_forced_into_a_type():
    result = document_classifier.classify(
        "Shopping list: two kilograms of rice, one litre of milk, a packet of tea."
    )
    assert result.certain is False


# ---------------------------------------------------------------- fact extraction


def test_rental_facts_are_read_from_the_right_place():
    facts = fact_extractor.extract_facts(
        segs(
            "The Tenant shall pay a monthly rent of Rs. 18,500/- every month.",
            "The Tenant has paid a security deposit of Rs. 1,10,000/- to the Landlord.",
            "The agreement is for a period of 11 months commencing from 1st April 2025 "
            "and expires on 28th February 2026.",
        ),
        "rental_agreement",
    )
    values = {fact.key: fact.value for fact in facts}
    assert values["rent"] == "Rs. 18,500"
    assert values["deposit"] == "Rs. 1,10,000"
    assert values["start_date"] == "1st April 2025"
    # The end date must be the date after "expires on", not the first in the line.
    assert values["end_date"] == "28th February 2026"


def test_total_amount_is_taken_after_its_trigger_not_first_in_the_block():
    facts = fact_extractor.extract_facts(
        segs(
            "Room rent Rs. 17,500.00 Pharmacy Rs. 14,870.00 "
            "Total amount payable by patient Rs. 30,100.00"
        ),
        "hospital_bill",
    )
    values = {fact.key: fact.value for fact in facts}
    assert values["total_amount"] == "Rs. 30,100.00"


def test_missing_fields_are_absent_rather_than_invented():
    facts = fact_extractor.extract_facts(
        segs("This page contains no amounts, no dates and no durations at all."),
        "rental_agreement",
    )
    assert {fact.key for fact in facts} == set()


def test_ambiguous_numeric_date_is_marked_uncertain():
    facts = fact_extractor.extract_facts(
        segs("The agreement shall commence with effect from 05/06/2025."),
        "rental_agreement",
    )
    start = next(fact for fact in facts if fact.key == "start_date")
    assert start.uncertain is True


def test_facts_keep_their_source_sentence_and_page():
    facts = fact_extractor.extract_facts(
        segs("The Tenant shall pay a monthly rent of Rs. 9,000/- per month."),
        "rental_agreement",
    )
    rent = next(fact for fact in facts if fact.key == "rent")
    assert "9,000" in rent.source_text
    assert rent.page == 1


# ---------------------------------------------------------------- clause detection


def test_detects_each_implemented_category():
    cases = {
        "auto_renewal": "This agreement shall stand renewed automatically for a further term of 11 months.",
        "penalty": "The Tenant shall pay a penalty of Rs. 250 per day of delay.",
        "late_payment": "If the rent is not paid on or before the 5th day, a late fee applies.",
        "extra_charges": "In addition to the rent, the Tenant shall pay maintenance charges of Rs. 2,400.",
        "lock_in": "There shall be a lock-in period of 6 months from the date of commencement.",
        "early_termination": "In case of early termination by the Tenant, one month rent is payable.",
        "deposit_deduction": "The Landlord may deduct unpaid dues from the security deposit amount.",
        "notice_period": "Either party may terminate by giving 2 months prior written notice.",
        "interest_rate": "The loan shall carry interest at the rate of 14.5% per annum.",
        "obligation": "The Tenant shall be responsible for all minor repairs to the premises.",
        "deadline": "The amount shall be remitted on or before 15th July 2025.",
        "unusual_condition": "The Lender may recall the loan at any time without assigning any reason.",
    }
    for category, sentence in cases.items():
        clauses = clause_detector.detect_clauses(segs(sentence))
        found = {clause.category for clause in clauses}
        assert category in found, "%s not detected in: %s" % (category, sentence)


def test_negative_phrases_veto_a_match():
    clauses = clause_detector.detect_clauses(
        segs("There shall be no lock-in period under this agreement whatsoever.")
    )
    assert "lock_in" not in {clause.category for clause in clauses}

    clauses = clause_detector.detect_clauses(
        segs("The security deposit is fully refundable and shall not be deducted.")
    )
    assert "deposit_deduction" not in {clause.category for clause in clauses}


def test_isolated_keyword_without_context_is_not_flagged():
    # "notice" here is a notice board, not a notice period.
    clauses = clause_detector.detect_clauses(
        segs("A copy of this agreement is displayed on the notice board in the lobby.")
    )
    assert "notice_period" not in {clause.category for clause in clauses}


def test_weak_deadline_wording_needs_a_date_or_duration():
    without = clause_detector.detect_clauses(
        segs("The parties shall act within the spirit of mutual cooperation always.")
    )
    assert "deadline" not in {clause.category for clause in without}

    with_date = clause_detector.detect_clauses(
        segs("The Borrower shall pay the amount within 7 days of such demand notice.")
    )
    assert "deadline" in {clause.category for clause in with_date}


def test_clause_keeps_original_text_page_and_reason():
    sentence = "The Tenant shall pay a penalty of Rs. 250 per day of delay."
    clause = clause_detector.detect_clauses(segs(sentence))[0]
    assert clause.text == sentence
    assert clause.page == 1
    assert clause.matched_terms
    assert "Matched wording" in clause.reason
    assert clause.suggested_action


def test_no_clause_is_labelled_illegal_or_fraudulent():
    for rule in clause_detector.RULES:
        blob = " ".join([rule["label"], rule["reason"], rule["action"]]).lower()
        for word in ("illegal", "fraud", "void", "unenforceable", "unlawful"):
            assert word not in blob, rule["category"]


def test_category_count_is_capped(rental_pdf_bytes):
    import pdf_reader

    pages, _info = pdf_reader.extract_pdf(rental_pdf_bytes)
    segments = build_segments((page.page, page.text) for page in pages)
    clauses = clause_detector.detect_clauses(segments, "rental_agreement")
    counts = {}
    for clause in clauses:
        counts[clause.category] = counts.get(clause.category, 0) + 1
    assert max(counts.values()) <= clause_detector.MAX_PER_CATEGORY
    assert len(clauses) <= 25


def test_detection_works_without_ollama(ollama_down, rental_pdf_bytes):
    import pdf_reader

    pages, _info = pdf_reader.extract_pdf(rental_pdf_bytes)
    segments = build_segments((page.page, page.text) for page in pages)
    assert clause_detector.detect_clauses(segments, "rental_agreement")


# ---------------------------------------------------------------- dates and deadlines


def test_date_parsing_formats():
    assert dates.parse_date("dated 12th March 2025")[0] == "2025-03-12"
    assert dates.parse_date("on March 12, 2025")[0] == "2025-03-12"
    assert dates.parse_date("on 2025-03-12")[0] == "2025-03-12"
    assert dates.parse_date("on 25/12/2025")[0] == "2025-12-25"
    # Day-first assumption, flagged as medium rather than claimed as certain.
    iso, _raw, confidence = dates.parse_date("on 05/06/2025")
    assert iso == "2025-06-05"
    assert confidence == "medium"
    # A month with no day cannot be a confident calendar date.
    assert dates.parse_date("in March 2025")[2] == "low"
    assert dates.parse_date("no date in this line")[0] is None


def test_impossible_date_is_rejected():
    assert dates.parse_date("on 31/02/2025")[0] is None


def test_amount_parsing():
    assert dates.find_amount("a sum of Rs. 1,10,000/- is payable") == "Rs. 1,10,000"
    assert dates.find_amount("the rate is 12 per cent") is None
    assert dates.find_percent("interest of 14.5% per annum") == "14.5%"
    assert dates.duration_days("a period of 2 months") == 60
    assert dates.duration_days("eleven months") == 330


def test_deadline_needs_deadline_wording_not_just_a_date():
    plain = deadline_extractor.extract_deadlines(
        segs("This agreement was executed on 1st April 2025 at Kochi between the parties.")
    )
    assert plain == []

    real = deadline_extractor.extract_deadlines(
        segs("The amount shall be remitted on or before 15th July 2025 at the counter.")
    )
    assert len(real) == 1
    assert real[0].date_iso == "2025-07-15"
    assert real[0].confidence == "high"
    assert real[0].verified is False
    assert "15th July 2025" in real[0].source_text


def test_one_deadline_per_date_even_with_several_cues():
    found = deadline_extractor.extract_deadlines(
        segs(
            "The total payable amount is due on or before 18th June 2025, and if not "
            "paid by the due date a late payment charge applies."
        )
    )
    assert len({item.date_iso for item in found}) == len(found)
    assert found[0].date_iso == "2025-06-18"


def test_relative_window_without_a_date_is_low_confidence():
    found = deadline_extractor.extract_deadlines(
        segs("You are required to submit a written objection within 15 days of receipt.")
    )
    assert found
    assert found[0].date_iso is None
    assert found[0].confidence == "low"
    assert "no explicit calendar date" in found[0].description
