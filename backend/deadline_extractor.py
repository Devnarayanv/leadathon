"""Deadline extraction.

A date in a document is not automatically a deadline. A sentence qualifies
only when deadline wording sits next to the date, or when a duration is tied
to an action ("within 30 days"). Everything else stays out, and the user
verifies what is left before it reaches a calendar.

Root cause of the old "deadline found but not shown" bug
-------------------------------------------------------
The fact extractor and this module each kept their own list of trigger
phrases, and the lists had drifted apart. "Please settle the bill by
18/06/2025" matched the fact extractor's "settle the bill by" and appeared as
"Payment due date" in Key Facts - but that phrase was not in DEADLINE_CUES, so
the Deadlines section said there were none. The same happened for "terminate
on", "end date", "remit ... by", tender "bid opening" dates and others. A
second, smaller loss came from de-duplicating on the date alone, which merged
two different deadlines that happened to fall on the same day.

Three changes close the gap:
  1. The cue list below is far wider and every cue carries a deadline type,
  2. reconcile_with_facts() promotes every date-valued, deadline-like fact
     into the deadline list when the cue pass missed it, so the two views can
     no longer disagree about whether a date is a deadline, and
  3. de-duplication is keyed on (date, type of deadline).
"""
import re
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import dates
from schemas import Deadline, Fact, Segment
from utils import fold_malayalam, normalise, normalise_phrase, truncate

# cue -> (deadline_type, description)
DEADLINE_CUES: Dict[str, Tuple[str, str]] = {
    # Generic, strong
    "on or before": ("action", "Action required on or before this date"),
    "no later than": ("action", "Action required by this date"),
    "not later than": ("action", "Action required by this date"),
    "last date": ("action", "Last date for the stated action"),
    "failing which": ("consequence", "Consequence applies after this date"),
    "due date": ("payment", "Payment or action due"),
    "due on": ("payment", "Payment or action due"),
    "payment due": ("payment", "Payment due"),
    "payable on or before": ("payment", "Payment due"),
    "payable by": ("payment", "Payment due"),
    "pay by": ("payment", "Payment due"),
    "settle the bill by": ("payment", "Bill to be settled"),
    "remit": ("payment", "Payment to be remitted"),
    "deposit the amount": ("payment", "Payment to be deposited"),
    "send payment": ("payment", "Payment to be sent"),
    # Expiry / validity
    "shall expire": ("expiry", "Agreement or notice expiry"),
    "expires on": ("expiry", "Expiry"),
    "expire on": ("expiry", "Expiry"),
    "expiry date": ("expiry", "Expiry"),
    "date of expiry": ("expiry", "Expiry"),
    "expiry of the": ("expiry", "Expiry of the stated period"),
    "valid upto": ("expiry", "Validity ends"),
    "valid up to": ("expiry", "Validity ends"),
    "valid until": ("expiry", "Validity ends"),
    "valid till": ("expiry", "Validity ends"),
    "terminate on": ("expiry", "Agreement ends"),
    "end date": ("expiry", "Agreement ends"),
    "shall end on": ("expiry", "Agreement ends"),
    # Renewal
    "renewal date": ("renewal", "Renewal due"),
    "due for renewal": ("renewal", "Renewal due"),
    "renewal": ("renewal", "Renewal decision point"),
    "renew": ("renewal", "Renewal decision point"),
    # Notice
    "notice period": ("notice", "Notice must be given before this point"),
    "prior notice": ("notice", "Notice must be given before this point"),
    # Agreement lifecycle
    "vacate": ("handover", "Hand-over / vacating date"),
    "commence": ("start", "Start of the agreement"),
    "with effect from": ("start", "Start of the agreement"),
    # Loans
    "repayment shall commence": ("emi", "First repayment"),
    "first instalment": ("emi", "First instalment"),
    "first installment": ("emi", "First instalment"),
    "first emi": ("emi", "First EMI"),
    "emi is scheduled": ("emi", "EMI due"),
    "scheduled for": ("action", "Scheduled date"),
    # Submissions, tenders, notices
    "submit": ("submission", "Submission deadline"),
    "submission": ("submission", "Submission deadline"),
    "closing date": ("submission", "Submission closes"),
    "bid submission closing": ("tender_submission", "Bid submission closes"),
    "last date for submission": ("tender_submission", "Bid submission closes"),
    "date and time of opening": ("tender_opening", "Bid opening"),
    "opening of online tender": ("tender_opening", "Bid opening"),
    "bid opening": ("tender_opening", "Bid opening"),
    "tender opening": ("tender_opening", "Bid opening"),
    "pre-bid meeting": ("tender_meeting", "Pre-bid meeting"),
    "appear before": ("appearance", "Appearance deadline"),
    "show cause": ("reply", "Reply deadline"),
    "reply by": ("reply", "Reply deadline"),
    "respond by": ("reply", "Reply deadline"),
    "reply within": ("reply", "Reply deadline"),
    "deliver by": ("delivery", "Delivery due"),
    "delivery date": ("delivery", "Delivery due"),
    "required by": ("delivery", "Required by"),
    "claim intimation": ("claim", "Claim must be intimated"),
    "intimate the claim": ("claim", "Claim must be intimated"),
    "within": ("relative", "Time limit from the stated event"),
    # Malayalam
    "മുൻപ് നൽകണം": ("payment", "Payment or action due before this date"),
    "അവസാന തീയതി": ("action", "Last date for the stated action"),
    "തീയതിക്ക് മുൻപ്": ("action", "Action required before this date"),
    "കാലാവധി": ("expiry", "Validity or period ends"),
}

TYPE_TITLES = {
    "payment": "Payment due",
    "expiry": "Expiry",
    "renewal": "Renewal",
    "notice": "Notice deadline",
    "handover": "Hand-over",
    "start": "Start date",
    "emi": "EMI due",
    "submission": "Submission deadline",
    "tender_submission": "Bid submission closes",
    "tender_opening": "Bid opening",
    "tender_meeting": "Pre-bid meeting",
    "appearance": "Appearance",
    "reply": "Reply deadline",
    "delivery": "Delivery due",
    "claim": "Claim intimation",
    "consequence": "Deadline",
    "action": "Deadline",
    "relative": "Time limit",
    "recurring": "Recurring payment",
}

# Dates that describe the past, not a deadline.
PAST_CUES = (
    "dated", "date of birth", "issued on", "executed on", "signed on",
    "date of admission", "date of bill", "bill date", "invoice date",
    "as on", "incorporated on",
)

STRONG_CUES = {
    "on or before", "no later than", "not later than", "last date", "due date", "due on",
    "payment due", "failing which", "payable by", "payable on or before", "pay by",
    "settle the bill by", "expires on", "expire on", "shall expire", "expiry date",
    "date of expiry", "valid upto", "valid up to", "valid until", "valid till",
    "terminate on", "end date", "shall end on", "renewal date", "due for renewal",
    "submit", "submission", "closing date", "bid submission closing",
    "last date for submission", "date and time of opening", "opening of online tender",
    "bid opening", "tender opening", "pre-bid meeting", "appear before", "show cause",
    "reply by", "respond by", "reply within", "deliver by", "delivery date",
    "required by", "first emi", "emi is scheduled", "repayment shall commence",
    "first instalment", "first installment", "remit", "deposit the amount",
    "send payment", "claim intimation", "intimate the claim",
    "മുൻപ് നൽകണം", "അവസാന തീയതി", "തീയതിക്ക് മുൻപ്",
}

# Cues too weak to carry a deadline on their own without an explicit date.
WEAK_CUES = {"renew", "renewal", "within", "commence", "vacate", "scheduled for"}

_WORD_NUM = (r"\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
             r"fifteen|thirty|sixty|ninety")
_WITHIN = re.compile(
    r"within\s+(?:a\s+period\s+of\s+)?(%s)\s*[-\s]?(day|days|week|weeks|month|months|year|years)\b"
    % _WORD_NUM,
    re.IGNORECASE,
)
# OCR turns "within 30 days" into "witin 30 drys" and similar; accept the
# near-misses so a scanned invoice's payment terms are not lost.
# "Net 30 days" is the standard invoice way of saying "within 30 days".
_WITHIN_OCR = re.compile(
    r"(?:\bwit?h?[il1]n|\bnet)\s+(\d{1,3})\s*(d[a-z]{1,3}s|days?|weeks?|months?)\b",
    re.IGNORECASE,
)

_TIME = re.compile(
    r"\b((?:[01]?\d|2[0-3])[.:][0-5]\d\s*(?:a\.?m\.?|p\.?m\.?|hrs?|hours)?|"
    r"(?:1[0-2]|0?[1-9])\s*(?:a\.?m\.?|p\.?m\.?))(?![\w])",
    re.IGNORECASE,
)

# "on or before the 5th day of every English calendar month"
_RECURRING = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:day\s+)?of\s+(?:every|each)\s+(?:english\s+)?"
    r"(?:calendar\s+)?month\b",
    re.IGNORECASE,
)
# "at least 30 days before 28th February 2026" / "30 days prior to ..."
_DAYS_BEFORE = re.compile(
    r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|thirty|sixty|ninety)"
    r"\s+days?\s+(?:before|prior\s+to)\b",
    re.IGNORECASE,
)
_NUMBER_WORDS = dict(dates.WORD_NUMBERS, fifteen=15, thirty=30, sixty=60, ninety=90)

# Fact keys whose date IS a deadline, and the type it carries.
FACT_DEADLINE_KEYS: Dict[str, Tuple[str, str]] = {
    "due_date": ("payment", "Payment due"),
    "deadline": ("reply", "Response deadline"),
    "end_date": ("expiry", "Agreement ends"),
    "expiry_date": ("expiry", "Expiry / renewal"),
    "submission_deadline": ("tender_submission", "Bid submission closes"),
    "opening_date": ("tender_opening", "Bid opening"),
    "delivery_date": ("delivery", "Delivery due"),
}

_CONF_RANK = {"high": 0, "medium": 1, "low": 2}


def _cue_hits(haystack: str) -> List[Tuple[str, int]]:
    """Cues found in the text, in document order.

    A longer cue that contains a shorter one ("bid submission closing" vs
    "submission") wins at the same position, so the deadline is described by
    the most specific wording the document used.
    """
    found = []
    for cue in DEADLINE_CUES:
        index = haystack.find(normalise_phrase(cue))
        if index != -1:
            found.append((cue, index))
    found.sort(key=lambda row: (row[1], -len(row[0])))
    kept: List[Tuple[str, int]] = []
    for cue, index in found:
        end = index + len(normalise_phrase(cue))
        if any(k_i <= index and end <= k_i + len(normalise_phrase(k)) for k, k_i in kept):
            continue
        kept.append((cue, index))
    return kept


def _time_near(text: str, start: int) -> Optional[str]:
    window = text[start : start + 60]
    # Don't mistake the date itself (12.03.2025) for a time.
    window = dates.NUMERIC_DATE.sub(" ", window)
    match = _TIME.search(window)
    if not match:
        return None
    value = match.group(1).strip()
    # A bare "12.50" with no am/pm/hrs is as likely to be money as a time.
    if not re.search(r"[ap]\.?m|hr|hour", value, re.IGNORECASE) and ":" not in value:
        return None
    return value


def _title(deadline_type: str, text: str) -> str:
    lowered = text.lower()
    if deadline_type in ("payment", "relative"):
        if "rent" in lowered:
            return "Rent payment due"
        if "invoice" in lowered or "payment" in lowered and "receiv" in lowered:
            return "Invoice payment due"
        if "tax" in lowered or "gst" in lowered:
            return "Tax payment due"
        if "premium" in lowered:
            return "Premium payment due"
    if deadline_type == "expiry":
        if "policy" in lowered or "insurance" in lowered:
            return "Policy expiry"
        if "licen" in lowered or "registration" in lowered:
            return "Licence expiry"
        if "agreement" in lowered or "lease" in lowered or "tenancy" in lowered:
            return "Agreement expiry"
    if deadline_type == "reply" and ("gst" in lowered or "tax" in lowered):
        return "GST notice reply"
    return TYPE_TITLES.get(deadline_type, "Deadline")


def _within_days(match: re.Match) -> Optional[int]:
    raw = match.group(1).lower()
    count = _NUMBER_WORDS.get(raw)
    if count is None:
        try:
            count = int(raw)
        except ValueError:
            return None
    unit = match.group(2).lower()
    if unit.startswith("w"):
        return count * 7
    if unit.startswith("m"):
        return count * 30
    if unit.startswith("y"):
        return count * 365
    return count


def _recurring_deadlines(segment: Segment, text: str, search_text: str) -> List[Tuple[bool, Deadline]]:
    """A monthly obligation with no calendar date. Kept as a recurring item
    that needs verification, never turned into a single invented date."""
    out = []
    for match in _RECURRING.finditer(search_text):
        day = int(match.group(1))
        if not 1 <= day <= 31:
            continue
        out.append(
            (
                True,
                Deadline(
                    id=0,
                    title=_title("payment", text) if "pay" in text.lower() or "rent" in text.lower() else "Recurring deadline",
                    deadline_type="recurring",
                    date_iso=None,
                    date_text=match.group(0),
                    description="Payment or action due on day %d of every month" % day,
                    source_text=truncate(text, 300),
                    page=segment.page,
                    confidence="medium",
                    evidence_status="extracted",
                    needs_verification=True,
                    recurrence="monthly, day %d" % day,
                    verified=False,
                ),
            )
        )
    return out


def _days_before_deadlines(segment: Segment, text: str, search_text: str) -> List[Tuple[bool, Deadline]]:
    """"at least 30 days before <date>": the notice date is calculated from the
    stated date. The formula is shown in the description and the item is
    marked as calculated, so it is checked before it reaches a calendar."""
    out = []
    for match in _DAYS_BEFORE.finditer(search_text):
        raw = match.group(1).lower()
        days = int(raw) if raw.isdigit() else _NUMBER_WORDS.get(raw)
        if not days:
            continue
        iso, raw_date, confidence = dates.parse_date(search_text[match.end(): match.end() + 60])
        if not iso:
            continue
        anchor = date.fromisoformat(iso)
        calculated = (anchor - timedelta(days=days)).isoformat()
        out.append(
            (
                True,
                Deadline(
                    id=0,
                    title="Notice deadline",
                    deadline_type="notice",
                    date_iso=calculated,
                    date_text="%s days before %s" % (match.group(1), raw_date),
                    description="Notice must be given by this date (%d days before %s)" % (days, raw_date),
                    source_text=truncate(text, 300),
                    page=segment.page,
                    confidence="low" if confidence == "low" else "medium",
                    evidence_status="calculated",
                    needs_verification=True,
                    verified=False,
                ),
            )
        )
    return out


_DATE_TIME = re.compile(
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\s*[,]?\s*"
    r"((?:[01]?\d|2[0-3])[.:][0-5]\d\s*(?:a\.?m\.?|p\.?m\.?|hrs?)?)?",
    re.IGNORECASE,
)


def _tender_table_deadlines(segments: List[Segment]) -> List[Tuple[bool, Deadline]]:
    """Tender schedules printed as a table.

    E-tender notices put "bid submission closing date and time" and "date and
    time of opening" in column headers, and the values on each work's row as
    "30/11/2026 6.55 pm 02/12/2026 11.00 am" - nowhere near the header text,
    so the sentence-level cue pass cannot connect them. When the document has
    both headers, a row holding two date(+time) pairs is read in header order.
    """
    full = normalise(" ".join(s.text for s in segments))
    has_close = "submission closing" in full or "closing date" in full
    has_open = "opening of" in full or "bid opening" in full or "time of opening" in full
    if not (has_close and has_open):
        return []
    out: List[Tuple[bool, Deadline]] = []
    seen = set()
    for segment in segments:
        pairs = list(_DATE_TIME.finditer(segment.text))
        if len(pairs) < 2:
            continue
        for match, (deadline_type, title) in zip(
            pairs[-2:],
            (("tender_submission", "Bid submission closes"), ("tender_opening", "Bid opening")),
        ):
            iso, raw, conf = dates.parse_date(match.group(1))
            if not iso or (iso, deadline_type) in seen:
                continue
            seen.add((iso, deadline_type))
            out.append((True, Deadline(
                id=0, title=title, deadline_type=deadline_type, date_iso=iso,
                date_text=raw, time_text=(match.group(2) or "").strip() or None,
                description="%s (read from the tender schedule table)" % title,
                source_text=truncate(segment.text, 300), page=segment.page,
                confidence=conf, evidence_status="extracted" if conf == "high" else "needs_verification",
                needs_verification=conf != "high", origin="table",
            )))
    return out


def extract_deadlines(segments: List[Segment], max_items: int = 25) -> List[Deadline]:
    """One sentence can hold more than one deadline, so each cue is resolved
    against the date that follows it rather than the first date in the line."""
    out: List[Tuple[bool, Deadline]] = _tender_table_deadlines(segments)

    for segment in segments:
        text = segment.text.strip()
        if len(text) < 12:
            continue
        haystack = normalise(text)
        # Same reason as in fact_extractor: fold once, then search and slice
        # that one copy so offsets stay valid.
        search_text = fold_malayalam(text)
        lowered = search_text.lower()

        out.extend(_recurring_deadlines(segment, text, search_text))
        out.extend(_days_before_deadlines(segment, text, search_text))

        cue_hits = _cue_hits(haystack)
        if not cue_hits and _WITHIN_OCR.search(search_text) and re.search(
            r"pa[yv]|remit|settle|due", haystack
        ):
            # Payment terms on a scanned invoice often survive OCR only as
            # "witin 30 drys"; the time window is still real, so treat it as
            # the "within" cue it was printed as.
            cue_hits = [("within", 0)]
        if not cue_hits:
            continue

        past_only = any(cue in haystack for cue in PAST_CUES)
        has_strong = any(cue in STRONG_CUES for cue, _ in cue_hits)
        # "Net 30 days from the invoice date" mentions the invoice date as
        # the anchor of a deadline, not as a record of the past.
        anchored_window = bool(_WITHIN.search(search_text) or _WITHIN_OCR.search(search_text))
        if past_only and not has_strong and not anchored_window:
            # "dated 12/03/2025" with no deadline wording: a record, not a deadline.
            continue

        for cue, _position in cue_hits:
            start = lowered.find(normalise_phrase(cue))
            start = 0 if start == -1 else start + len(cue)
            iso, raw_date, date_confidence = dates.parse_date_after(search_text, start)
            relative = (
                _WITHIN.search(search_text[start:]) or _WITHIN.search(search_text)
                or _WITHIN_OCR.search(search_text)
            )
            if not iso and not relative:
                continue

            strong = cue in STRONG_CUES
            if not strong and cue in WEAK_CUES and not iso:
                if not (cue == "within" and relative):
                    continue

            deadline_type, description = DEADLINE_CUES[cue]
            if iso:
                date_text = raw_date
                confidence = date_confidence if strong else "low"
                # A day-month order that could be read either way, or a month
                # with no day, is not something to put in a calendar unchecked.
                needs_verification = date_confidence != "high"
            else:
                date_text = relative.group(0)
                confidence = "low"
                if deadline_type in ("action", "submission", "consequence"):
                    deadline_type = "relative"
                description = description + " (no explicit calendar date in the document; counted from an event)"
                needs_verification = True

            out.append(
                (
                    strong,
                    Deadline(
                        id=0,
                        title=_title(deadline_type, text),
                        deadline_type=deadline_type,
                        date_iso=iso,
                        date_text=date_text,
                        time_text=_time_near(search_text, start) if iso else None,
                        description=description,
                        source_text=truncate(text, 300),
                        page=segment.page,
                        confidence=confidence,
                        evidence_status="needs_verification" if needs_verification else "extracted",
                        needs_verification=needs_verification,
                        verified=False,
                        origin="cue",
                    ),
                )
            )

    out = _dedupe(out)
    return _finalise([d for _s, d in out], max_items)


_GENERIC = ("action", "consequence", "submission", "relative")


def _dedupe(candidates: List[Tuple[bool, Deadline]]) -> List[Tuple[bool, Deadline]]:
    """One entry per (date, kind of deadline).

    Several cues can point at the same date in one sentence, and the user wants
    one calendar item, described by the strongest cue. But two *different*
    deadlines on the same day - bid submission and a pre-bid meeting, say - are
    both kept, which the old date-only key silently merged.
    """
    best: Dict[Tuple[str, str], Tuple[bool, Deadline]] = {}
    for strong, deadline in candidates:
        group = "_generic" if deadline.deadline_type in _GENERIC else deadline.deadline_type
        # An EMI is a payment; "EMI due" and "Payment due" on one date are one event.
        if group == "payment":
            group = "emi"
        key = (deadline.date_iso or deadline.date_text.lower(), group)
        current = best.get(key)
        if current is None:
            best[key] = (strong, deadline)
            continue
        current_strong, current_deadline = current
        better = (not current_strong and strong) or (
            current_strong == strong
            and _CONF_RANK[deadline.confidence] < _CONF_RANK[current_deadline.confidence]
        )
        if better:
            best[key] = (strong, deadline)

    # A generic entry and a specific entry on the same date are the same event
    # described twice; keep the specific description.
    specific_dates = {k[0] for k in best if k[1] != "_generic"}
    return [
        value for key, value in best.items()
        if not (key[1] == "_generic" and key[0] in specific_dates)
    ]


def reconcile_with_facts(deadlines: List[Deadline], facts: List[Fact],
                         max_items: int = 25) -> List[Deadline]:
    """Make sure every deadline-like fact also appears as a deadline.

    This is the fix for the reported bug. A date the fact extractor labelled as
    a due date, end date or response deadline is shown in Key Facts; if the cue
    pass did not find the same date, it is added here, quoted from the same
    sentence, so the Deadlines tab and the Overview always agree.
    """
    present = {d.date_iso for d in deadlines if d.date_iso}
    added: List[Deadline] = []
    for fact in facts:
        spec = FACT_DEADLINE_KEYS.get(fact.key)
        if not spec:
            continue
        iso, raw, conf = dates.parse_date(fact.value)
        if not iso or iso in present:
            continue
        deadline_type, title = spec
        source = fact.source_text or fact.value
        needs_verification = conf != "high" or fact.uncertain
        folded = fold_malayalam(source)
        position = folded.find(raw) if raw else -1
        added.append(
            Deadline(
                id=0,
                title=_title(deadline_type, source) if deadline_type != "tender_opening" else title,
                deadline_type=deadline_type,
                date_iso=iso,
                date_text=raw or fact.value,
                time_text=_time_near(folded, position + len(raw)) if position >= 0 else None,
                description='%s (from the "%s" field)' % (title, fact.label),
                source_text=truncate(source, 300),
                page=fact.page,
                confidence="medium" if needs_verification else fact.confidence,
                evidence_status="needs_verification" if needs_verification else "extracted",
                needs_verification=needs_verification,
                origin="field",
            )
        )
        present.add(iso)
    return _finalise(list(deadlines) + added, max_items)


def resolve_relative(deadlines: List[Deadline], facts: List[Fact]) -> List[Deadline]:
    """Turn "within 30 days of receiving this invoice" into a date, carefully.

    Only when the document itself states the anchor (the invoice or notice
    date) and the wording ties the window to the document. The result is
    labelled "calculated" and still needs the user's confirmation, because
    "receiving" may be later than the printed date.
    """
    anchor_fact = None
    for key in ("invoice_date", "notice_date", "po_date", "bill_date", "issue_date"):
        anchor_fact = next((f for f in facts if f.key == key), None)
        if anchor_fact:
            break
    if not anchor_fact:
        return deadlines
    anchor_iso, _raw, _conf = dates.parse_date(anchor_fact.value)
    if not anchor_iso:
        return deadlines
    anchor = date.fromisoformat(anchor_iso)

    resolved: List[Deadline] = []
    for deadline in deadlines:
        if deadline.date_iso is None and not deadline.recurrence:
            match = _WITHIN.search(deadline.date_text) or _WITHIN_OCR.search(deadline.date_text)
            context = deadline.source_text.lower()
            tied = any(word in context for word in (
                "invoice", "inv", "receipt", "receiv", "recen", "notice", "this bill",
                "date of", "issue"))
            days = _within_days(match) if match else None
            if days and tied:
                target = anchor + timedelta(days=days)
                is_payment = "pay" in context
                deadline = deadline.model_copy(update={
                    "date_iso": target.isoformat(),
                    "description": "%s + %d days (%s). Confirm when the period actually starts."
                    % (anchor_fact.label, days, deadline.date_text),
                    "evidence_status": "calculated",
                    "needs_verification": True,
                    "deadline_type": "payment" if is_payment else deadline.deadline_type,
                    "title": _title("payment", context) if is_payment else deadline.title,
                })
        resolved.append(deadline)
    return _finalise(resolved, len(resolved) or 1)


def _finalise(deadlines: List[Deadline], max_items: int) -> List[Deadline]:
    deadlines = sorted(
        deadlines,
        key=lambda d: (d.date_iso is None, d.date_iso or "9999", _CONF_RANK[d.confidence], d.page or 0),
    )[:max_items]
    for position, deadline in enumerate(deadlines, start=1):
        deadline.id = position
    return deadlines
