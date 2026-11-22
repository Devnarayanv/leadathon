"""Deadline extraction.

A date in a document is not automatically a deadline. A sentence qualifies
only when deadline wording sits next to the date, or when a duration is tied
to an action ("within 30 days"). Everything else stays out, and the user
verifies what is left before it reaches a calendar.
"""
import re
from typing import Dict, List, Optional, Tuple

import dates
from schemas import Deadline, Segment
from utils import fold_malayalam, normalise, normalise_phrase, truncate

# phrase -> what the deadline is about
DEADLINE_CUES: Dict[str, str] = {
    "on or before": "Action required on or before this date",
    "no later than": "Action required by this date",
    "not later than": "Action required by this date",
    "last date": "Last date for the stated action",
    "failing which": "Consequence applies after this date",
    "due date": "Payment or action due",
    "due on": "Payment or action due",
    "payable on or before": "Payment due",
    "payable by": "Payment due",
    "shall expire": "Agreement or notice expiry",
    "expires on": "Agreement or notice expiry",
    "expire on": "Agreement or notice expiry",
    "expiry of the": "Expiry of the stated period",
    "valid upto": "Validity ends",
    "valid up to": "Validity ends",
    "renewal": "Renewal decision point",
    "renew": "Renewal decision point",
    "notice period": "Notice must be given before this point",
    "prior notice": "Notice must be given before this point",
    "vacate": "Hand-over / vacating date",
    "commence": "Start of the agreement",
    "with effect from": "Start of the agreement",
    "repayment shall commence": "First repayment",
    "first instalment": "First instalment",
    "first installment": "First instalment",
    "submit": "Submission deadline",
    "appear before": "Appearance deadline",
    "show cause": "Reply deadline",
    "within": "Time limit from the stated event",
    # Malayalam
    "മുൻപ് നൽകണം": "Payment or action due before this date",
    "അവസാന തീയതി": "Last date for the stated action",
    "തീയതിക്ക് മുൻപ്": "Action required before this date",
    "കാലാവധി": "Validity or period ends",
}

# Dates that describe the past, not a deadline.
PAST_CUES = (
    "dated", "date of birth", "issued on", "executed on", "signed on",
    "date of admission", "date of bill", "bill date", "invoice date",
    "as on", "incorporated on",
)

_WITHIN = re.compile(
    r"within\s+(?:a\s+period\s+of\s+)?(\d{1,3}|one|two|three|four|five|six|seven|eight|"
    r"nine|ten|eleven|twelve)\s*[-\s]?(day|days|week|weeks|month|months|year|years)",
    re.IGNORECASE,
)


STRONG_CUES = (
    "on or before",
    "no later than",
    "not later than",
    "last date",
    "due date",
    "due on",
    "failing which",
    "payable by",
    "payable on or before",
    "expires on",
    "expire on",
    "shall expire",
    "valid upto",
    "valid up to",
    "submit",
    "appear before",
    "show cause",
    "മുൻപ് നൽകണം",
    "അവസാന തീയതി",
    "തീയതിക്ക് മുൻപ്",
)

# Cues too weak to carry a deadline on their own.
WEAK_CUES = ("renew", "within", "commence", "vacate", "submit")


def _cue_hits(haystack: str) -> List[Tuple[str, int]]:
    hits = [(cue, haystack.find(normalise_phrase(cue))) for cue in DEADLINE_CUES]
    found = [(cue, index) for cue, index in hits if index != -1]
    found.sort(key=lambda row: row[1])
    return found


_CONF_RANK = {"high": 0, "medium": 1, "low": 2}


def _dedupe_by_date(candidates: List[Tuple[bool, Deadline]]) -> List[Tuple[bool, Deadline]]:
    """One entry per date. Several cues can point at the same date in one
    sentence; the user wants one calendar item, described by the strongest cue."""
    best: Dict[str, Tuple[bool, Deadline]] = {}
    for strong, deadline in candidates:
        key = deadline.date_iso or deadline.date_text.lower()
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
    return list(best.values())


def extract_deadlines(segments: List[Segment], max_items: int = 15) -> List[Deadline]:
    """One sentence can hold more than one deadline, so each cue is resolved
    against the date that follows it rather than the first date in the line."""
    out: List[Tuple[bool, Deadline]] = []
    next_id = 1

    for segment in segments:
        text = segment.text.strip()
        if len(text) < 20:
            continue
        haystack = normalise(text)
        # Same reason as in fact_extractor: fold once, then search and slice
        # that one copy so offsets stay valid.
        search_text = fold_malayalam(text)
        lowered = search_text.lower()
        cue_hits = _cue_hits(haystack)
        if not cue_hits:
            continue

        past_only = any(cue in haystack for cue in PAST_CUES)
        has_strong = any(cue in STRONG_CUES for cue, _ in cue_hits)
        if past_only and not has_strong:
            # "dated 12/03/2025" with no deadline wording: a record, not a deadline.
            continue

        for cue, _position in cue_hits:
            start = lowered.find(normalise_phrase(cue))
            start = 0 if start == -1 else start + len(cue)
            iso, raw_date, date_confidence = dates.parse_date_after(search_text, start)
            relative = _WITHIN.search(search_text[start:]) or _WITHIN.search(search_text)
            if not iso and not relative:
                continue

            strong = cue in STRONG_CUES
            if not strong and cue in WEAK_CUES and not iso:
                continue

            description = DEADLINE_CUES[cue]
            if iso:
                date_text = raw_date
                confidence = date_confidence if strong else "low"
            else:
                # A relative window with no anchor date cannot reach a calendar.
                date_text = relative.group(0)
                confidence = "low"
                description += " (no explicit calendar date in the document)"

            out.append(
                (
                    strong,
                    Deadline(
                        id=next_id,
                        date_iso=iso,
                        date_text=date_text,
                        description=description,
                        source_text=truncate(text, 300),
                        page=segment.page,
                        confidence=confidence,
                        verified=False,
                    ),
                )
            )
            next_id += 1

    out = _dedupe_by_date(out)

    deadlines = [d for _strong, d in out]
    deadlines.sort(
        key=lambda d: (_CONF_RANK[d.confidence], d.date_iso or "9999", d.page or 0)
    )
    deadlines = deadlines[:max_items]
    for position, deadline in enumerate(deadlines, start=1):
        deadline.id = position
    return deadlines
