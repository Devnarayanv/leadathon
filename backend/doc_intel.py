"""Field extraction for the structured document types.

Every value here is copied from a line of the document's own text, or it is
absent. A label the text does not contain yields no Fact. Nothing is defaulted,
guessed or summed to fill a gap, so a missing figure stays missing all the way
to the verification report.

Money comes back formatted the way Indian documents write it (Rs. 3,050.00)
and is re-read through money.parse wherever arithmetic happens.
"""
import re
from typing import List, Optional, Sequence, Tuple

import money
from schemas import Fact, PageText, TenderRequirement

Hit = Tuple[int, str, str]  # page, source line, normalised value

_DATE = re.compile(
    r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b"
    r"|\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)
_PERCENT = re.compile(r"\d{1,3}(?:\.\d{1,3})?\s*(?:%|per\s*cent|percent)", re.IGNORECASE)
_YEARS = re.compile(r"(\d{1,3})\s*(?:years?|yrs?)\b", re.IGNORECASE)
_MONTHS = re.compile(r"(\d{1,3})\s*(?:months?|mos?)\b", re.IGNORECASE)
# A "Label: value" line. Used to keep labelled header rows out of item tables.
_LABELLED = re.compile(r"^\s*[A-Za-z][A-Za-z .()&/-]{0,50}:")
_BULLET = re.compile(r"^\s*(?:\d{1,2}[.)]|[a-z][.)]|\(\w{1,3}\)|[-•*▪])\s+(.+)$", re.IGNORECASE)
_HEADING = re.compile(
    r"eligib|qualification|requirement|documents?\s*(?:required|to\s*be\s*(?:submitted|uploaded)|list)|checklist",
    re.IGNORECASE,
)

# (key, label, label pattern, value kind, match anywhere in the line)
Spec = Tuple[str, str, str, str, bool]

_TAX = [
    ("cgst", "CGST", r"cgst", "money", False),
    ("cgst_rate", "CGST rate", r"cgst", "percent", False),
    ("sgst", "SGST", r"sgst", "money", False),
    ("sgst_rate", "SGST rate", r"sgst", "percent", False),
    ("igst", "IGST", r"igst", "money", False),
    ("igst_rate", "IGST rate", r"igst", "percent", False),
]

INVOICE: List[Spec] = [
    ("invoice_number", "Invoice number", r"invoice\s*(?:no\.?|number|#)|inv\.?\s*no\.?|bill\s*no\.?", "text", False),
    ("invoice_date", "Invoice date", r"invoice\s*date|bill\s*date|dated", "date", False),
    ("supplier", "Supplier", r"supplier|seller|sold\s*by|from|vendor", "text", False),
    ("buyer", "Buyer", r"buyer|bill\s*to|sold\s*to|customer", "text", False),
    ("subtotal", "Subtotal", r"sub\s*total", "money", False),
    ("taxable_value", "Taxable value", r"taxable\s*(?:value|amount)", "money", False),
    ("discount", "Discount", r"discount", "money", False),
    *_TAX,
    ("total", "Total", r"grand\s*total|total\s*amount|amount\s*payable|net\s*payable|total", "money", False),
]

PURCHASE_ORDER: List[Spec] = [
    ("po_number", "PO number", r"(?:purchase\s*order|p\.?o\.?)\s*(?:no\.?|number|#)|po\s*no\.?", "text", False),
    ("po_date", "PO date", r"(?:purchase\s*order|p\.?o\.?|order)\s*date|dated", "date", False),
    ("supplier", "Supplier", r"supplier|vendor|to", "text", False),
    ("buyer", "Buyer", r"buyer|ordered\s*by|bill\s*to|issued\s*by", "text", False),
    ("subtotal", "Subtotal", r"sub\s*total", "money", False),
    ("discount", "Discount", r"discount", "money", False),
    *_TAX,
    ("total", "Total", r"grand\s*total|total\s*amount|order\s*value|total", "money", False),
]

TENDER: List[Spec] = [
    ("tender_number", "Tender number", r"tender\s*(?:no\.?|number|id|reference)|nit\s*no\.?|bid\s*no\.?", "text", False),
    ("issuing_authority", "Issuing authority", r"issued\s*by|issuing\s*authority|organisation|organization", "text", False),
    ("estimated_value", "Estimated value", r"estimated\s*(?:value|cost)|tender\s*value", "money", False),
    ("emd", "EMD", r"emd|earnest\s*money(?:\s*deposit)?", "money", False),
    ("emd_percent", "EMD percentage", r"emd|earnest\s*money(?:\s*deposit)?", "percent", False),
    ("submission_deadline", "Submission deadline",
     r"last\s*date\s*(?:of|for|to)\s*(?:bid\s*)?submi(?:ssion|t)|bid\s*submission(?:\s*deadline)?|submission\s*deadline", "date", False),
    ("opening_date", "Bid opening date", r"bid\s*opening(?:\s*date)?|opening\s*date", "date", False),
    ("turnover_required", "Minimum annual turnover",
     r"(?:minimum\s*)?(?:average\s*)?annual\s*turnover", "money", True),
    ("experience_required", "Experience required", r"experience", "years", True),
]

GST_NOTICE: List[Spec] = [
    ("notice_number", "Notice reference number", r"din|reference\s*(?:no\.?|number)|notice\s*(?:no\.?|number)", "text", False),
    ("notice_date", "Notice date", r"date\s*of\s*(?:issue|notice)|notice\s*date", "date", False),
    ("section", "Section cited", r"section", "text", False),
    ("tax_period", "Tax period", r"tax\s*period|period", "text", False),
    ("tax_demanded", "Tax demanded", r"tax\s*(?:demanded|payable|demand)|demand\s*amount|amount\s*demanded", "money", False),
    ("interest_demanded", "Interest demanded", r"interest", "money", False),
    ("penalty", "Penalty", r"penalty", "money", False),
    ("reply_by", "Reply due by", r"reply\s*(?:by|within|due)|last\s*date\s*to\s*reply|respond\s*by", "date", False),
]

LOAN: List[Spec] = [
    ("principal", "Loan amount (principal)", r"loan\s*amount|principal|sanctioned\s*amount", "money", False),
    ("annual_rate", "Annual interest rate",
     r"(?:annual\s*)?(?:interest\s*)?rate(?:\s*of\s*interest)?|interest\s*rate", "percent", False),
    ("tenure_months", "Tenure", r"tenure|repayment\s*period|loan\s*period|term", "months", False),
    ("emi", "Monthly EMI", r"emi|monthly\s*(?:installment|instalment|emi)", "money", False),
]

INSURANCE: List[Spec] = [
    ("policy_number", "Policy number", r"policy\s*(?:no\.?|number|id)", "text", False),
    ("insurer", "Insurer", r"insurer|insurance\s*company|issued\s*by", "text", False),
    ("sum_insured", "Sum insured", r"sum\s*insured", "money", False),
    ("premium", "Total premium", r"total\s*premium|premium\s*payable|net\s*premium|premium", "money", False),
    ("policy_start", "Policy start date",
     r"policy\s*start(?:\s*date)?|period\s*from|inception|start\s*date|valid\s*from", "date", False),
    ("policy_end", "Policy end date",
     r"policy\s*end(?:\s*date)?|period\s*to|expiry(?:\s*date)?|end\s*date|valid\s*(?:till|until|to)", "date", False),
    ("deductible", "Deductible", r"deductible|excess", "money", False),
]

RENTAL: List[Spec] = [
    ("monthly_rent", "Monthly rent", r"monthly\s*rent|rent", "money", False),
    ("rent_escalation", "Annual rent escalation", r"annual\s*escalation|rent\s*escalation|escalation", "percent", False),
]

SPECS = {
    "invoice": INVOICE,
    "purchase_order": PURCHASE_ORDER,
    "tender": TENDER,
    "gst_notice": GST_NOTICE,
    "loan_agreement": LOAN,
    "insurance": INSURANCE,
    "rental_agreement": RENTAL,
}


def _label_re(pattern: str, anywhere: bool) -> "re.Pattern[str]":
    if anywhere:
        head = r"(?:^[\s\-•*▪|]*|(?<=[\s(;,]))"
    else:
        head = r"^[\s\-•*▪|]*"
    return re.compile(head + r"(?:%s)\b\s*[:\-–]?\s*(?P<rest>.*)$" % pattern, re.IGNORECASE)


def _plain(value) -> str:
    return f"{value.normalize():f}"


def _value(kind: str, rest: str) -> Optional[str]:
    if kind == "text":
        text = rest.strip(" :-–|").strip()
        return text[:160] or None
    if kind == "money":
        parsed = money.parse(_PERCENT.sub(" ", rest))
        return money.fmt(parsed) if parsed is not None else None
    if kind == "percent":
        parsed = money.parse_percent(rest)
        return f"{_plain(parsed)}%" if parsed is not None else None
    if kind == "date":
        match = _DATE.search(rest)
        return match.group(0) if match else None
    if kind == "months":
        match = _MONTHS.search(rest)
        if match:
            return "%d months" % int(match.group(1))
        years = _YEARS.search(rest)
        if years:
            return "%d months" % (int(years.group(1)) * 12)
        return None
    if kind == "years":
        years = _YEARS.search(rest)
        return "%d years" % int(years.group(1)) if years else None
    return None


def _find(pages: Sequence[PageText], pattern: str, kind: str, anywhere: bool = False) -> Optional[Hit]:
    """First line, in document order, whose label matches and whose value parses."""
    regex = _label_re(pattern, anywhere)
    for page in pages:
        for raw in (page.text or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            match = regex.search(line)
            if not match:
                continue
            value = _value(kind, match.group("rest"))
            if value:
                return page.page, line[:300], value
    return None


def fields(doc_type: str, pages: Sequence[PageText]) -> List[Fact]:
    """Labelled fields the document states. Absent labels produce no Fact."""
    facts: List[Fact] = []
    for key, label, pattern, kind, anywhere in SPECS.get(doc_type, []):
        hit = _find(pages, pattern, kind, anywhere)
        if hit is None:
            continue
        page, line, value = hit
        facts.append(
            Fact(
                key=key,
                label=label,
                value=value,
                page=page,
                source_text=line,
                confidence="high",
                evidence_status="extracted",
            )
        )
    return facts


def item_source(pages: Sequence[PageText]) -> List[Tuple[int, str]]:
    """Page text with date lines and "Label: value" lines removed.

    Those lines look like table rows to the item parser (a date is three
    numbers) but they are header or total lines, so they are kept out.
    """
    out: List[Tuple[int, str]] = []
    for page in pages:
        kept = []
        for raw in (page.text or "").splitlines():
            line = raw.strip()
            if not line or _DATE.search(line) or _LABELLED.match(line):
                continue
            kept.append(line)
        out.append((page.page, "\n".join(kept)))
    return out


_KIND_RULES = [
    ("financial", r"turnover|net\s*worth|balance\s*sheet|financial|profit"),
    ("technical", r"experience|similar\s*(?:work|project)|completed|projects?"),
    ("eligibility", r"certif|iso|registration|licen[cs]e|gst|pan\b|msme|udyam"),
    ("document", r"document|copy|affidavit|undertaking|self[- ]attested|form|annexure|proof"),
]


def _requirement_kind(text: str, heading_hint: str) -> str:
    for kind, pattern in _KIND_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return kind
    return heading_hint


def tender_requirements(pages: Sequence[PageText], max_items: int = 40) -> List[TenderRequirement]:
    """Bulleted or numbered lines under an eligibility or document heading."""
    items: List[TenderRequirement] = []
    seen = set()
    remaining = 0
    hint = "eligibility"
    for page in pages:
        for raw in (page.text or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            if _HEADING.search(line) and len(line) < 120 and not _BULLET.match(line):
                remaining = 25
                hint = "document" if re.search(r"document|checklist", line, re.IGNORECASE) else "eligibility"
                continue
            if remaining <= 0:
                continue
            remaining -= 1
            bullet = _BULLET.match(line)
            if not bullet:
                continue
            text = bullet.group(1).strip()[:300]
            key = text.lower()
            if key in seen or len(items) >= max_items:
                continue
            seen.add(key)
            if re.search(r"\bmandatory\b|\bmust\b|\bshall\b", text, re.IGNORECASE):
                mandatory: Optional[bool] = True
            elif re.search(r"\boptional\b|\bpreferred\b|\bdesirable\b", text, re.IGNORECASE):
                mandatory = False
            else:
                mandatory = None
            items.append(
                TenderRequirement(
                    label=text[:90],
                    description=text,
                    mandatory=mandatory,
                    page=page.page,
                    source_text=line[:300],
                    kind=_requirement_kind(text, hint),
                )
            )
    return items


REQUIRED_FIELDS = {
    "invoice": [("invoice_number", "Invoice number"), ("invoice_date", "Invoice date"),
                ("supplier", "Supplier"), ("buyer", "Buyer"), ("total", "Total")],
    "purchase_order": [("po_number", "PO number"), ("po_date", "PO date"),
                       ("supplier", "Supplier"), ("buyer", "Buyer"), ("total", "Total")],
    "tender": [("tender_number", "Tender number"), ("submission_deadline", "Submission deadline"),
               ("emd", "EMD")],
    "gst_notice": [("notice_number", "Notice reference number"), ("tax_demanded", "Tax demanded"),
                   ("reply_by", "Reply due by")],
    "loan_agreement": [("principal", "Loan amount"), ("annual_rate", "Annual interest rate"),
                       ("tenure_months", "Tenure")],
    "insurance": [("policy_number", "Policy number"), ("sum_insured", "Sum insured"),
                  ("premium", "Total premium"), ("policy_end", "Policy end date")],
    "rental_agreement": [("monthly_rent", "Monthly rent")],
}
