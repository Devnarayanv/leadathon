"""Rule-based fact extraction. Regex and keywords only, never an LLM.

Every fact carries the sentence it came from and its page, so a judge (or a
user) can check it against the original document. Nothing is guessed: a field
with no match is simply absent, and the dashboard shows "Not found".
"""
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import dates
from schemas import Fact, Segment
from utils import fold_malayalam, normalise, normalise_phrase, truncate

# key, label, trigger phrases, extractor, anti-phrases
Spec = Dict

# Every extractor takes (segment_text, offset). offset is where the trigger
# phrase was found, so a sentence holding two amounts or two dates yields the
# one that belongs to this field rather than whichever came first.


def _amount_near(segment_text: str, offset: int = 0) -> Optional[str]:
    return dates.find_amount_after(segment_text, offset, require_currency=True)


def _amount_loose(segment_text: str, offset: int = 0) -> Optional[str]:
    return dates.find_amount_after(segment_text, offset, require_currency=False)


def _percent(segment_text: str, offset: int = 0) -> Optional[str]:
    return dates.find_percent_after(segment_text, offset)


def _duration(segment_text: str, offset: int = 0) -> Optional[str]:
    return dates.find_duration_after(segment_text, offset)


def _date(segment_text: str, offset: int = 0) -> Optional[str]:
    iso, raw, _conf = dates.parse_date_after(segment_text, offset)
    return raw if iso else None


def _sentence(segment_text: str, offset: int = 0) -> Optional[str]:
    return truncate(segment_text, 220)


def _reference(segment_text: str, offset: int = 0) -> Optional[str]:
    match = re.search(
        r"(?:ref(?:erence)?|notice|file|bill|invoice|uhid|ip|account)\s*"
        r"(?:no\.?|number|#)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9/\-]{3,25})",
        segment_text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _authority(segment_text: str, offset: int = 0) -> Optional[str]:
    match = re.search(
        r"((?:office of the |the )?[A-Z][A-Za-z.&]*(?:\s+[A-Z][A-Za-z.&]*){0,5}"
        r"\s+(?:Department|Corporation|Municipality|Panchayat|Authority|Board|Tribunal|Commission|Office))",
        segment_text,
    )
    if match:
        return truncate(match.group(1), 90)
    match = re.search(r"(Government of [A-Z][A-Za-z ]{2,30})", segment_text)
    return truncate(match.group(1), 90) if match else None


def _amount_percent_or_sentence(segment_text: str, offset: int = 0) -> Optional[str]:
    """A fee can be "Rs. 500" or "2% of the amount": take whichever the
    document puts nearer the label, not whichever type we happen to try first."""
    window = segment_text[offset : offset + dates.AFTER_WINDOW] if offset else segment_text
    amount = dates.CURRENCY_AMOUNT.search(window) or dates.MALAYALAM_AMOUNT.search(window)
    percent = dates.PERCENT.search(window)
    if amount and percent:
        return (
            dates.format_amount(amount)
            if amount.start() < percent.start()
            else percent.group(0).strip()
        )
    if amount:
        return dates.format_amount(amount)
    if percent:
        return percent.group(0).strip()
    return (
        dates.find_amount_after(segment_text, offset, require_currency=True)
        or dates.find_percent_after(segment_text, offset)
        or truncate(segment_text, 180)
    )


COMMON_SPECS: List[Spec] = [
    {
        "key": "penalty",
        "label": "Penalty / late fee",
        "triggers": ["penalty", "penal interest", "late fee", "late payment charge",
                     "fine of", "പിഴ"],
        "extract": _amount_percent_or_sentence,
        "confidence": "medium",
    },
    {
        "key": "notice_period",
        "label": "Notice period",
        "triggers": ["notice period", "months notice", "month notice", "days notice",
                     "prior notice", "advance notice", "written notice of",
                     "നോട്ടീസ് കാലാവധി", "നോട്ടീസ്"],
        "extract": _duration,
        "confidence": "high",
    },
]

SPECS_BY_TYPE: Dict[str, List[Spec]] = {
    "rental_agreement": [
        {
            "key": "rent",
            "label": "Monthly rent",
            "triggers": ["monthly rent", "rent of rs", "rent shall be", "licence fee",
                         "license fee", "rent per month", "payable as rent",
                         "പ്രതിമാസ വാടക", "വാടക"],
            "extract": _amount_near,
            "confidence": "high",
        },
        {
            "key": "deposit",
            "label": "Security deposit",
            "triggers": ["security deposit", "caution deposit", "advance deposit",
                         "interest free deposit", "refundable deposit",
                         "ഡിപ്പോസിറ്റ്", "മുൻകൂർ തുക"],
            "extract": _amount_near,
            "confidence": "high",
        },
        {
            "key": "start_date",
            "label": "Start date",
            "triggers": ["commence", "commencing", "with effect from", "start date",
                         "effective from", "shall begin"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "end_date",
            "label": "End date",
            "triggers": ["expire", "expiry", "end date", "terminate on", "until",
                         "valid upto", "valid up to"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "duration",
            "label": "Agreement duration",
            "triggers": ["period of", "term of", "duration of", "for a term",
                         "tenure of", "months commencing",
                         "കരാർ കാലാവധി", "കാലാവധി"],
            "extract": _duration,
            "confidence": "medium",
        },
        {
            "key": "lock_in",
            "label": "Lock-in period",
            "triggers": ["lock-in", "lock in period", "minimum period of occupation",
                         "ലോക്ക് ഇൻ"],
            "extract": _duration,
            "confidence": "high",
        },
        {
            "key": "renewal",
            "label": "Renewal condition",
            "triggers": ["renew", "renewal", "extended for a further",
                         "automatically renewed"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "maintenance",
            "label": "Maintenance / extra charges",
            "triggers": ["maintenance charge", "society charge", "electricity charge",
                         "water charge", "additional charge"],
            "extract": _amount_percent_or_sentence,
            "confidence": "medium",
        },
    ],
    "loan_agreement": [
        {
            "key": "loan_amount",
            "label": "Loan amount",
            "triggers": ["loan amount", "principal amount", "sanctioned amount",
                         "facility amount", "amount of loan", "sanction of rs",
                         "വായ്പ തുക", "വായ്പ"],
            "extract": _amount_near,
            "confidence": "high",
        },
        {
            "key": "interest_rate",
            "label": "Interest rate",
            "triggers": ["rate of interest", "interest rate", "interest at",
                         "per annum", "p.a.", "പലിശ നിരക്ക്", "പലിശ"],
            "extract": _percent,
            "confidence": "high",
        },
        {
            "key": "emi",
            "label": "EMI",
            "triggers": ["emi", "equated monthly", "monthly instalment",
                         "monthly installment"],
            "extract": _amount_near,
            "confidence": "high",
        },
        {
            "key": "repayment_duration",
            "label": "Repayment duration",
            "triggers": ["repayment period", "tenure", "repayable in", "term of the loan",
                         "number of instalments", "number of installments"],
            "extract": _duration,
            "confidence": "medium",
        },
        {
            "key": "processing_fee",
            "label": "Processing fee",
            "triggers": ["processing fee", "processing charge", "documentation charge",
                         "administrative fee"],
            "extract": _amount_percent_or_sentence,
            "confidence": "high",
        },
        {
            "key": "due_date",
            "label": "Payment due date",
            "triggers": ["due date", "payable on or before", "first instalment",
                         "first installment", "repayment shall commence"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "prepayment",
            "label": "Prepayment / foreclosure",
            "triggers": ["prepayment", "pre-payment", "foreclosure", "part payment charge"],
            "extract": _amount_percent_or_sentence,
            "confidence": "medium",
        },
    ],
    "hospital_bill": [
        {
            "key": "total_amount",
            "label": "Total amount",
            "triggers": ["total amount", "grand total", "net payable", "total payable",
                         "amount due", "bill amount", "total bill",
                         "ആകെ തുക", "ആകെ"],
            "extract": _amount_near,
            "confidence": "high",
        },
        {
            "key": "bill_date",
            "label": "Bill date",
            "triggers": ["bill date", "invoice date", "date of bill", "billing date",
                         "discharge date", "date of discharge"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "due_date",
            "label": "Payment due date",
            "triggers": ["due date", "payable by", "payable on or before",
                         "settle the bill by"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "reference",
            "label": "Bill / patient reference",
            "triggers": ["bill no", "invoice no", "uhid", "ip no", "patient id"],
            "extract": _reference,
            "confidence": "medium",
        },
        {
            "key": "major_charges",
            "label": "Major charge heads",
            "triggers": ["room rent", "consultation charge", "pharmacy", "surgery charge",
                         "investigation charge", "nursing charge", "laboratory"],
            "extract": _amount_percent_or_sentence,
            "confidence": "medium",
        },
        {
            "key": "payment_info",
            "label": "Payment information",
            "triggers": ["mode of payment", "pay at the counter", "payment can be made",
                         "account number", "upi"],
            "extract": _sentence,
            "confidence": "low",
        },
    ],
    "government_notice": [
        {
            "key": "authority",
            "label": "Issuing authority",
            "triggers": ["department", "corporation", "panchayat", "authority",
                         "government of", "office of the", "municipality"],
            "extract": _authority,
            "confidence": "medium",
        },
        {
            "key": "notice_date",
            "label": "Notice date",
            "triggers": ["dated", "notice date", "date of issue", "issued on"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "deadline",
            "label": "Response deadline",
            "triggers": ["on or before", "within", "failing which", "last date",
                         "not later than"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "required_action",
            "label": "Required action",
            "triggers": ["hereby directed", "are required to", "you are requested to",
                         "shall submit", "show cause", "appear before"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "reference",
            "label": "Reference number",
            "triggers": ["reference no", "ref no", "file no", "notice no", "order no"],
            "extract": _reference,
            "confidence": "medium",
        },
        {
            "key": "amount_demanded",
            "label": "Amount demanded",
            "triggers": ["amount of rs", "dues of", "payable", "arrears", "tax due"],
            "extract": _amount_near,
            "confidence": "medium",
        },
    ],
    "other": [
        {
            "key": "amount",
            "label": "Amount mentioned",
            "triggers": ["rs.", "rs ", "inr", "amount", "total"],
            "extract": _amount_near,
            "confidence": "low",
        },
        {
            "key": "date",
            "label": "Date mentioned",
            "triggers": ["date", "dated", "on or before", "within"],
            "extract": _date,
            "confidence": "low",
        },
        {
            "key": "duration",
            "label": "Duration mentioned",
            "triggers": ["period of", "term of", "months", "years"],
            "extract": _duration,
            "confidence": "low",
        },
    ],
}


def _trigger_hits(haystack: str, triggers: Sequence[str]) -> List[Tuple[str, int]]:
    """Every trigger that appears, with its position, in document order."""
    hits = [(t, haystack.find(normalise_phrase(t))) for t in triggers]
    found = [(t, i) for t, i in hits if i != -1]
    found.sort(key=lambda row: row[1])
    return found


def extract_facts(segments: List[Segment], doc_type: str) -> List[Fact]:
    """One pass over the segments, first confident match per key wins."""
    specs = list(SPECS_BY_TYPE.get(doc_type, SPECS_BY_TYPE["other"])) + COMMON_SPECS
    found: Dict[str, Fact] = {}

    for segment in segments:
        # normalise() only lowercases and collapses whitespace, so positions in
        # the normalised string line up closely enough with the original for
        # "look after the trigger" to work on either.
        haystack = normalise(segment.text)
        # Chillu folding changes string length, so an offset taken from folded
        # text would mis-slice the raw text. Search AND slice the same folded
        # copy; values are digits or dates, which folding leaves untouched, and
        # source_text below still quotes the document verbatim.
        search_text = fold_malayalam(segment.text)
        lowered = search_text.lower()
        for spec in specs:
            key = spec["key"]
            if key in found:
                continue
            hits = _trigger_hits(haystack, spec["triggers"])
            if not hits:
                continue

            extractor: Callable[..., Optional[str]] = spec["extract"]
            value: Optional[str] = None
            trigger = hits[0][0]
            offset = 0
            for candidate, _position in hits:
                # Use the position in the ORIGINAL text; whitespace collapsing
                # can shift the normalised index.
                start = lowered.find(normalise_phrase(candidate))
                start = 0 if start == -1 else start + len(candidate)
                candidate_value = extractor(search_text, start)
                if candidate_value:
                    trigger, offset, value = candidate, start, candidate_value
                    break
            if not value:
                continue

            uncertain = False
            confidence = spec.get("confidence", "medium")
            # A numeric date read day-first could also be month-first.
            if extractor is _date:
                iso, _raw, date_conf = dates.parse_date_after(search_text, offset)
                if iso and date_conf != "high":
                    uncertain = True
                    confidence = "low" if date_conf == "low" else "medium"
            found[key] = Fact(
                key=key,
                label=spec["label"],
                value=value,
                page=segment.page,
                source_text=truncate(segment.text, 300),
                confidence=confidence,
                uncertain=uncertain,
            )

    # Preserve spec order so the dashboard reads predictably.
    ordered: List[Fact] = []
    for spec in specs:
        fact = found.get(spec["key"])
        if fact:
            ordered.append(fact)
    return ordered


def expected_fact_labels(doc_type: str) -> List[Dict[str, str]]:
    """Fields this document type is expected to carry.

    The dashboard uses this to render "Not found" rows rather than silently
    omitting a field the user is looking for.
    """
    specs = list(SPECS_BY_TYPE.get(doc_type, SPECS_BY_TYPE["other"])) + COMMON_SPECS
    return [{"key": s["key"], "label": s["label"]} for s in specs]
