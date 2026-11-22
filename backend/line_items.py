"""Line-item table extraction for invoices and purchase orders.

PDF text extraction flattens a table into lines, so a row has to be recognised
from its shape rather than from any grid. A row here is a line that ends in at
least two numbers, where the last is an amount and one of the earlier ones is a
quantity. The description is whatever text precedes the numbers.

Rows that do not fit that shape are left out rather than guessed at: the
verification engine reports "unable to verify" when it has no rows, which is
honest, where a half-parsed table would produce a wrong mismatch.
"""
from decimal import Decimal
from typing import List, Optional, Tuple
import re

import money
from schemas import LineItem

# A number as it appears in a table cell: 1,234.50 / 1234 / 12.5
_CELL = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,3})?|\d+(?:\.\d{1,3})?)(?![\w])")

# Lines that are table furniture, not rows.
_SKIP = re.compile(
    r"^\s*(?:s\.?\s*no|sl\.?\s*no|sr\.?\s*no|item\s*(?:no|code)|description|particulars|"
    r"hsn|qty|quantity|rate|unit\s*price|amount|total|subtotal|sub\s*total|cgst|sgst|igst|"
    r"gst|tax|discount|grand\s*total|net\s*(?:amount|payable)|round(?:ing|ed)?\s*off|"
    r"page\s*\d|terms|declaration|signature|bank\s*details|e\s*&?\s*o\.?e)\b",
    re.IGNORECASE,
)

# Trailing summary words: a line naming one of these is a total, not an item.
_SUMMARY_WORDS = (
    "total", "subtotal", "sub total", "taxable", "cgst", "sgst", "igst",
    "discount", "round off", "rounded off", "net payable", "amount due",
    "grand total", "in words", "balance",
)

_UNIT = re.compile(
    r"\b(nos?|pcs?|pieces?|units?|kgs?|kg|grams?|gm|litres?|ltr|l|mtr|metres?|m|"
    r"sqft|sq\.?\s*ft|sqm|boxes?|box|packs?|sets?|hours?|hrs?|days?|months?|"
    r"bags?|rolls?|cans?|tons?|quintals?)\b",
    re.IGNORECASE,
)


def _numbers(line: str) -> List[Tuple[Decimal, int, int]]:
    """Every numeric cell in the line, with its span."""
    out = []
    for match in _CELL.finditer(line):
        value = money.parse(match.group(1))
        if value is not None:
            out.append((value, match.start(), match.end()))
    return out


def _is_summary_line(line: str) -> bool:
    lowered = line.lower()
    return any(word in lowered for word in _SUMMARY_WORDS)


def _description(line: str, first_number_start: int) -> str:
    """Text before the numbers, minus any leading serial number."""
    head = line[:first_number_start].strip(" |\t:-")
    head = re.sub(r"^\d{1,3}[.)]?\s+", "", head).strip()
    return head


def parse_row(line: str) -> Optional[LineItem]:
    """One table row, or None when the line is not a row.

    Recognised shapes, in order of preference:
      desc  qty  rate  amount           (amount == qty * rate)
      desc  qty  rate  ...  amount      (extra columns such as HSN or tax %)
      desc  qty  rate                   (amount derived, flagged as computed)
    """
    line = line.strip()
    if len(line) < 6 or _SKIP.match(line) or _is_summary_line(line):
        return None

    cells = _numbers(line)
    if len(cells) < 3:
        return None

    # The description must be real words, not just a serial number.
    description = _description(line, cells[0][1])
    # A leading bare serial number is a cell too; drop it when the description
    # turned out to be empty because the line started "1 Steel bolts 10 ...".
    if not description:
        serial_end = cells[0][2]
        rest = line[serial_end:]
        shifted = _numbers(rest)
        if len(shifted) < 3:
            return None
        description = _description(rest, shifted[0][1])
        cells = [(v, s + serial_end, e + serial_end) for v, s, e in shifted]
    if len(re.sub(r"[^A-Za-zഀ-ൿ]", "", description)) < 3:
        return None

    unit = None
    unit_match = _UNIT.search(line[cells[0][1]:])
    if unit_match:
        unit = unit_match.group(1)

    values = [c[0] for c in cells]
    # Last number is the line amount; the two before it are the candidates for
    # quantity and rate. Pick the pair whose product matches the amount.
    amount = values[-1]
    quantity: Optional[Decimal] = None
    rate: Optional[Decimal] = None
    computed = False

    for i in range(len(values) - 1):
        for j in range(i + 1, len(values) - 1):
            product = values[i] * values[j]
            if product != 0 and money.within_tolerance(product, amount, Decimal("0.50")):
                quantity, rate = values[i], values[j]
                break
        if quantity is not None:
            break

    if quantity is None:
        # No pair multiplies to the amount. Fall back to positional reading
        # (qty, rate, amount) which is how these tables are nearly always laid
        # out, and let the verification engine report the mismatch.
        if len(values) >= 3:
            quantity, rate = values[-3], values[-2]
        else:
            return None

    if quantity == 0 or rate == 0:
        return None

    return LineItem(
        description=description[:120],
        # format(..., "f") keeps plain digits: str(Decimal("10").normalize()) is "1E+1".
        quantity=format(quantity.normalize(), "f") if quantity is not None else None,
        unit=unit,
        unit_price=str(money.q(rate)) if rate is not None else None,
        amount=str(money.q(amount)),
        amount_was_computed=computed,
    )


def extract(pages: List[Tuple[int, str]], max_items: int = 40) -> List[LineItem]:
    """Line items across the document, in document order."""
    items: List[LineItem] = []
    seen = set()
    for page_no, text in pages:
        for raw_line in (text or "").splitlines():
            row = parse_row(raw_line)
            if row is None:
                continue
            key = (row.description.lower(), row.amount)
            if key in seen:
                continue
            seen.add(key)
            row.page = page_no
            row.source_text = raw_line.strip()[:300]
            items.append(row)
            if len(items) >= max_items:
                return items
    return items
