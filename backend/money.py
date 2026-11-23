"""Exact money arithmetic for Doc Decode's verification engine.

Every figure that reaches a verification check goes through here first, so the
arithmetic is Decimal from end to end. Float addition of 1,23,456.78 style
amounts drifts by fractions of a paisa, and a verification report that says
"off by Rs. 0.00" is worse than no report at all.

Nothing in this module invents a value. parse() returns None when the text
holds no readable amount, and the callers are required to treat None as
"the document did not state this" rather than as zero.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional
import re

TWO_PLACES = Decimal("0.01")

# Indian grouping (12,34,567.89), plain (1234567.89), and the trailing "/-"
# that Indian invoices use in place of a decimal part.
_NUMBER = re.compile(
    r"(?<![\d.])"
    r"(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)"
    r"(?![\d])"
)

_SCALE = {
    "lakh": Decimal(100000),
    "lakhs": Decimal(100000),
    "lac": Decimal(100000),
    "lacs": Decimal(100000),
    "crore": Decimal(10000000),
    "crores": Decimal(10000000),
    "thousand": Decimal(1000),
    "ലക്ഷം": Decimal(100000),
    "കോടി": Decimal(10000000),
}

_SCALE_RE = re.compile(
    r"\s*(lakhs?|lacs?|crores?|thousand|ലക്ഷം|കോടി)\b", re.IGNORECASE
)


def parse(text: Optional[str]) -> Optional[Decimal]:
    """The first money value in `text`, as an exact Decimal.

    Handles "Rs. 1,23,456.78", "₹ 45000/-", "2.5 lakh", "18,500 രൂപ" and bare
    numbers. Returns None when there is no number at all - never 0.
    """
    if not text:
        return None
    cleaned = str(text).strip()
    match = _NUMBER.search(cleaned)
    if not match:
        return None
    try:
        value = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    scale = _SCALE_RE.match(cleaned[match.end():])
    if scale:
        value *= _SCALE[scale.group(1).lower()]
    return value


def parse_percent(text: Optional[str]) -> Optional[Decimal]:
    """A percentage as a Decimal number of percent (18% -> Decimal('18'))."""
    if not text:
        return None
    match = re.search(r"(\d{1,3}(?:\.\d{1,3})?)\s*(?:%|per\s*cent|percent)", str(text), re.IGNORECASE)
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except InvalidOperation:
        return None


_CURRENCY_SIGNS = (
    ("₹", "Rs."), ("rs.", "Rs."), ("rs ", "Rs."), ("inr", "Rs."), ("രൂപ", "Rs."),
    ("us$", "$"), ("usd", "$"), ("$", "$"),
    ("eur", "€"), ("€", "€"), ("gbp", "£"), ("£", "£"),
    ("aed", "AED"), ("sar", "SAR"),
)


def detect_currency(text: Optional[str], default: str = "Rs.") -> str:
    """The currency a document writes its amounts in.

    Used only for display. Verification arithmetic never converts between
    currencies - a document is checked against itself.
    """
    if not text:
        return default
    lowered = str(text).lower()
    best: Optional[tuple] = None
    for needle, symbol in _CURRENCY_SIGNS:
        index = lowered.find(needle)
        if index != -1 and (best is None or index < best[0]):
            best = (index, symbol)
    return best[1] if best else default


def q(value: Decimal) -> Decimal:
    """Round to paise, half-up, the way an accountant would."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def fmt(value: Optional[Decimal], currency: str = "Rs.") -> str:
    """Indian-grouped display string. Returns an em dash for a missing value,
    so a UI never prints "0.00" for something the document did not state."""
    if value is None:
        return "—"
    value = q(value)
    sign = "-" if value < 0 else ""
    whole, _, frac = str(abs(value)).partition(".")
    frac = (frac + "00")[:2]
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    # "Rs. 1,148.00" reads with a space; "$1,148.00" does not.
    space = " " if currency and currency[-1].isalpha() or currency.endswith(".") else ""
    return f"{currency}{space}{sign}{whole}.{frac}"


def within_tolerance(a: Decimal, b: Decimal, tolerance: Decimal = Decimal("1.00")) -> bool:
    """True when two amounts agree closely enough to call a match.

    One rupee of slack absorbs the rounding a supplier's own software applied
    per line, without hiding a real discrepancy - the smallest mismatch worth
    showing a user is larger than that.
    """
    return abs(q(a) - q(b)) <= tolerance


def pct_of(base: Decimal, percent: Decimal) -> Decimal:
    return q(base * percent / Decimal(100))
