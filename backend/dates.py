"""Shared date and money pattern parsing.

Indian documents mix dd/mm/yyyy, 12th March 2025 and 2025-03-12. Day-first is
assumed for ambiguous numeric dates, which is the convention in the documents
this app targets; anything genuinely ambiguous is reported as such instead of
being silently resolved.
"""
import re
from datetime import date
from typing import Optional, Tuple

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

# 12/03/2025, 12-03-25, 12.03.2025
NUMERIC_DATE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
# 2025-03-12
ISO_DATE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
# 12th March 2025 / 12 Mar, 2025
DAY_MONTH_YEAR = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(%s)[a-z]*\.?,?\s+(\d{4})\b" % _MONTH_ALT,
    re.IGNORECASE,
)
# March 12, 2025
MONTH_DAY_YEAR = re.compile(
    r"\b(%s)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b" % _MONTH_ALT,
    re.IGNORECASE,
)
# March 2025 (no day)
MONTH_YEAR = re.compile(r"\b(%s)[a-z]*\.?,?\s+(\d{4})\b" % _MONTH_ALT, re.IGNORECASE)

# Rs. 15,000 / INR 15000 / 15,000/- / Rs 1.5 lakh
AMOUNT = re.compile(
    r"(?:(?:rs\.?|inr|₹)\s*)?"
    r"(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
    r"\s*(?:/-)?"
    r"\s*(lakhs?|lacs?|crores?|thousand)?",
    re.IGNORECASE,
)
CURRENCY_AMOUNT = re.compile(
    r"(?:rs\.?|inr|₹)\s*(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
    r"\s*(?:/-)?\s*(lakhs?|lacs?|crores?|thousand)?",
    re.IGNORECASE,
)
# Malayalam writes the unit after the number: "18,500 രൂപ". ലക്ഷം = lakh.
MALAYALAM_AMOUNT = re.compile(
    r"(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(?:/-)?\s*"
    r"(ലക്ഷം|കോടി)?\s*"
    r"രൂപ"
)
PERCENT = re.compile(r"(\d{1,3}(?:\.\d{1,2})?)\s*(?:%|per\s*cent|percent)", re.IGNORECASE)
DURATION = re.compile(
    r"\b(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*"
    r"[-\s]?(day|days|week|weeks|month|months|year|years)\b",
    re.IGNORECASE,
)

# Malayalam puts the unit after the number: "11 മാസം". Written in the folded
# (consonant + virama) form, because the text being searched is folded too.
_ML_UNITS = {
    "ദിവസ": 1,  # ദിവസ(ം) - day
    "ആഴ്ച": 7,  # ആഴ്ച - week
    "മാസ": 30,  # മാസ(ം) - month
    "വര്ഷ": 365,  # വര്ഷ(ം) - year (folded ർ)
}
MALAYALAM_DURATION = re.compile(
    # The trailing anusvara is part of the word (മാസം) but not of the stem used
    # for the lookup, so it is matched outside the capturing group.
    r"(\d{1,3})\s*(%s)ം?" % "|".join(sorted(_ML_UNITS, key=len, reverse=True))
)

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}
MULTIPLIERS = {
    "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000,
    "crore": 10000000, "crores": 10000000, "thousand": 1000,
}


def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _expand_year(year: int) -> int:
    if year >= 100:
        return year
    # Two-digit years in these documents are 2000s in practice.
    return 2000 + year


def parse_date(text: str) -> Tuple[Optional[str], str, str]:
    """Find the first date in text.

    Returns (iso_date_or_None, matched_text, confidence).
    confidence is "high" for unambiguous dates, "medium" where day/month order
    could be read either way, "low" for a month without a day.
    """
    match = ISO_DATE.search(text)
    if match:
        year, month, day = (int(g) for g in match.groups())
        parsed = _safe_date(year, month, day)
        if parsed:
            return parsed.isoformat(), match.group(0), "high"

    match = DAY_MONTH_YEAR.search(text)
    if match:
        day = int(match.group(1))
        month = MONTHS.get(match.group(2).lower())
        year = int(match.group(3))
        if month:
            parsed = _safe_date(year, month, day)
            if parsed:
                return parsed.isoformat(), match.group(0), "high"

    match = MONTH_DAY_YEAR.search(text)
    if match:
        month = MONTHS.get(match.group(1).lower())
        day = int(match.group(2))
        year = int(match.group(3))
        if month:
            parsed = _safe_date(year, month, day)
            if parsed:
                return parsed.isoformat(), match.group(0), "high"

    match = NUMERIC_DATE.search(text)
    if match:
        first, second, raw_year = (int(g) for g in match.groups())
        year = _expand_year(raw_year)
        # Day-first unless that is impossible.
        if first > 12 and second <= 12:
            parsed, confidence = _safe_date(year, second, first), "high"
        elif second > 12 and first <= 12:
            parsed, confidence = _safe_date(year, first, second), "high"
        else:
            parsed, confidence = _safe_date(year, second, first), "medium"
        if parsed:
            return parsed.isoformat(), match.group(0), confidence

    match = MONTH_YEAR.search(text)
    if match:
        month = MONTHS.get(match.group(1).lower())
        year = int(match.group(2))
        if month:
            parsed = _safe_date(year, month, 1)
            if parsed:
                # No day in the document, so the ISO day is an assumption.
                return parsed.isoformat(), match.group(0), "low"

    return None, "", "low"


def has_date(text: str) -> bool:
    return parse_date(text)[0] is not None


# A value belonging to a label sits close to it. Searching the whole block
# instead lets "Processing charges: 0.50%" pick up an unrelated "Rs. 28,410"
# from another line, which would report a number the document never gave for
# that field. Both windows are deliberately tight.
AFTER_WINDOW = 140
BEFORE_WINDOW = 90


def _windows(text: str, offset: int) -> Tuple[str, str]:
    """(text just after the trigger, text just before it)."""
    if offset <= 0:
        return text, ""
    return text[offset : offset + AFTER_WINDOW], text[max(0, offset - BEFORE_WINDOW) : offset]


def parse_date_after(text: str, offset: int) -> Tuple[Optional[str], str, str]:
    """The first date just after offset, else one just before it.

    A sentence like "for 11 months commencing from 1 April 2025 and expires on
    28 February 2026" holds two dates. Which one is the end date depends on
    where the trigger phrase sits, so the caller passes that position. A date
    further away than the windows is not treated as belonging to this field.
    """
    after, before = _windows(text, offset)
    iso, raw, confidence = parse_date(after)
    if iso:
        return iso, raw, confidence
    if before:
        iso, raw, confidence = parse_date(before)
        if iso:
            return iso, raw, confidence
    return None, "", "low"


def find_amount_after(
    text: str, offset: int, require_currency: bool = True
) -> Optional[str]:
    after, before = _windows(text, offset)
    return find_amount(after, require_currency) or (
        find_amount(before, require_currency) if before else None
    )


def find_percent_after(text: str, offset: int) -> Optional[str]:
    after, before = _windows(text, offset)
    return find_percent(after) or (find_percent(before) if before else None)


def find_duration_after(text: str, offset: int) -> Optional[str]:
    after, before = _windows(text, offset)
    return find_duration(after) or (find_duration(before) if before else None)


def parse_amount_value(digits: str, multiplier: Optional[str]) -> Optional[float]:
    try:
        value = float(digits.replace(",", ""))
    except ValueError:
        return None
    if multiplier:
        key = multiplier.lower().strip()
        factor = MULTIPLIERS.get(key) or MULTIPLIERS.get(key.rstrip("s")) or 1
        value *= factor
    return value


def format_amount(match: re.Match) -> str:
    """Render a money match the way the document wrote it.

    Malayalam amounts keep their own "രൂപ" suffix rather than being relabelled
    with "Rs.", because the value should read back the way the document says it.
    """
    raw = match.group(0).strip().rstrip("-/ ")
    if raw.lower().startswith(("rs", "inr", "₹")):
        return raw
    if "രൂപ" in raw:  # രൂപ
        return raw
    return "Rs. " + raw


def find_amount(text: str, require_currency: bool = True) -> Optional[str]:
    """First money value in text.

    With require_currency, a currency marker must be present: "Rs. 500",
    "₹500" or the Malayalam "500 രൂപ". Without it, any number counts.
    """
    if require_currency:
        candidates = []
        for pattern in (CURRENCY_AMOUNT, MALAYALAM_AMOUNT):
            match = pattern.search(text)
            if match:
                candidates.append(match)
        if not candidates:
            return None
        # Whichever marker appears first in the sentence.
        match = min(candidates, key=lambda m: m.start())
        return format_amount(match)

    match = AMOUNT.search(text)
    return format_amount(match) if match else None


def find_percent(text: str) -> Optional[str]:
    match = PERCENT.search(text)
    return match.group(0).strip() if match else None


def find_duration(text: str) -> Optional[str]:
    candidates = [m for m in (DURATION.search(text), MALAYALAM_DURATION.search(text)) if m]
    if not candidates:
        return None
    return min(candidates, key=lambda m: m.start()).group(0).strip()


def duration_days(text: str) -> Optional[int]:
    match = DURATION.search(text)
    if not match:
        malayalam = MALAYALAM_DURATION.search(text)
        if malayalam:
            try:
                count = int(malayalam.group(1))
            except ValueError:
                return None
            return count * _ML_UNITS[malayalam.group(2)]
        return None
    raw = match.group(1).lower()
    count = WORD_NUMBERS.get(raw)
    if count is None:
        try:
            count = int(raw)
        except ValueError:
            return None
    unit = match.group(2).lower().rstrip("s")
    per = {"day": 1, "week": 7, "month": 30, "year": 365}.get(unit)
    return count * per if per else None
