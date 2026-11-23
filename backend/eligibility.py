"""Tender eligibility checklist.

Each TenderRequirement is compared with what the user entered. The output is
four lists: meets, does_not_meet, missing (the user has not entered what is
needed), and needs_verification (the rule cannot read the requirement or the
match is not clear). This is a checklist aid. It never says the user is or is
not eligible; the tender authority decides that.
"""
import difflib
import re
from typing import Dict, List

import money
from schemas import (
    EligibilityRequest,
    EligibilityResponse,
    EligibilityRow,
    TenderRequirement,
)

DISCLAIMER = (
    "This is a checklist to help you read the tender. It is not a decision and "
    "Doc Decode cannot tell you whether you are eligible. The tender authority "
    "decides. Confirm each point against the tender text before you bid."
)

_KNOWN_CREDENTIALS = [
    r"ISO\s*\d{4,5}(?::\d{4})?",
    r"MSME|Udyam",
    r"GST(?:IN| registration)?",
    r"PAN",
    r"BIS",
    r"trade licen[cs]e",
]


def _row(requirement: TenderRequirement, detail: str = "") -> EligibilityRow:
    return EligibilityRow(
        requirement=requirement.label,
        detail=detail,
        page=requirement.page,
        source_text=requirement.source_text,
    )


def _contains_any(entries: List[str], needle: str) -> bool:
    needle = needle.lower()
    return any(needle in entry.lower() or entry.lower() in needle for entry in entries if entry.strip())


def _doc_matches(documents: List[str], requirement_text: str) -> bool:
    words = set(re.findall(r"[a-z]{4,}", requirement_text.lower()))
    for document in documents:
        doc_words = set(re.findall(r"[a-z]{4,}", document.lower()))
        if not doc_words:
            continue
        overlap = len(words & doc_words) / max(1, min(len(words), len(doc_words)))
        if overlap >= 0.5 or difflib.SequenceMatcher(None, document.lower(), requirement_text.lower()).ratio() >= 0.6:
            return True
    return False


def _check(requirement: TenderRequirement, request: EligibilityRequest) -> tuple:
    """Return (bucket, detail). bucket is one of the four list names."""
    text = "%s %s" % (requirement.label, requirement.description)

    if re.search(r"turnover", text, re.IGNORECASE):
        needed = money.parse(requirement.description or requirement.label)
        if needed is None:
            return "needs_verification", "The turnover threshold is not readable in the requirement text."
        if not request.turnover:
            return "missing", "Enter your annual turnover to check this (needed: %s)." % money.fmt(needed)
        have = money.parse(request.turnover)
        if have is None:
            return "missing", "The turnover you entered could not be read as an amount."
        if have >= needed:
            return "meets", "Your turnover %s is at least %s." % (money.fmt(have), money.fmt(needed))
        return "does_not_meet", "Your turnover %s is below %s." % (money.fmt(have), money.fmt(needed))

    years_match = re.search(r"(\d{1,2})\s*years?", text, re.IGNORECASE)
    if re.search(r"experience", text, re.IGNORECASE) and years_match:
        needed_years = int(years_match.group(1))
        if request.experience_years is None:
            return "missing", "Enter your years of experience to check this (needed: %d)." % needed_years
        if request.experience_years >= needed_years:
            return "meets", "You entered %g years of experience against %d required." % (request.experience_years, needed_years)
        return "does_not_meet", "You entered %g years of experience against %d required." % (request.experience_years, needed_years)

    credentials = list(request.certifications) + list(request.registrations)
    for pattern in _KNOWN_CREDENTIALS:
        found = re.search(pattern, text, re.IGNORECASE)
        if not found:
            continue
        needle = found.group(0)
        if not credentials:
            return "missing", "Enter your certificates and registrations to check for %s." % needle
        if _contains_any(credentials, needle):
            return "meets", "Your listed credentials include %s." % needle
        return "does_not_meet", "None of your listed credentials matches %s." % needle

    if re.search(r"document|copy|affidavit|undertaking|certificate|annexure|proof|form", text, re.IGNORECASE):
        if not request.documents:
            return "missing", "Enter the documents you hold to check this."
        if _doc_matches(request.documents, text):
            return "meets", "A document you listed appears to match this requirement."
        return "needs_verification", "No listed document clearly matches this. Check the document list yourself."

    return "needs_verification", "This requirement needs checking by hand. Doc Decode cannot compare it with your details."


def check(request: EligibilityRequest) -> EligibilityResponse:
    buckets: Dict[str, List[EligibilityRow]] = {
        "meets": [],
        "does_not_meet": [],
        "missing": [],
        "needs_verification": [],
    }
    for requirement in request.requirements:
        bucket, detail = _check(requirement, request)
        buckets[bucket].append(_row(requirement, detail))

    counts = {name: len(rows) for name, rows in buckets.items()}
    headline = (
        "%d point(s) appear to be met, %d not met, %d need your details, %d need checking by hand."
        % (counts["meets"], counts["does_not_meet"], counts["missing"], counts["needs_verification"])
    )
    if not request.requirements:
        headline = "No requirements were supplied, so there is nothing to check. Analyse a tender first."
    return EligibilityResponse(
        headline=headline,
        meets=buckets["meets"],
        does_not_meet=buckets["does_not_meet"],
        missing=buckets["missing"],
        needs_verification=buckets["needs_verification"],
        disclaimer=DISCLAIMER,
    )
