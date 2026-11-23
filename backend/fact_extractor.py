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


_LOOSE_NUMBER = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?![\d,]*\s*%)(?![\w])"
)


def _money(segment_text: str, offset: int = 0) -> Optional[str]:
    """An amount for a money field such as a subtotal, tax or total.

    A currency-marked amount is preferred. Failing that, the first number that
    is not a percentage and not part of a date: "Tax 15%: $1,148" is the tax
    1,148, and the rate 15 belongs to a different field. Totals on OCR'd
    invoices often lose their currency symbol, so a bare number is still taken
    when nothing better is in reach.
    """
    if offset:
        window = segment_text[offset : offset + dates.AFTER_WINDOW]
    else:
        window = segment_text
    marked = dates.CURRENCY_AMOUNT.search(window) or dates.MALAYALAM_AMOUNT.search(window)
    if marked:
        return dates.format_amount(marked)
    # Strip dates out before looking for a bare number.
    scrubbed = dates.NUMERIC_DATE.sub(" ", window)
    scrubbed = dates.ISO_DATE.sub(" ", scrubbed)
    for match in _LOOSE_NUMBER.finditer(scrubbed):
        raw = match.group(1)
        digits = raw.replace(",", "").split(".")[0]
        # A lone single digit is almost always a serial number or a column
        # index, not an amount.
        if len(digits) < 2:
            continue
        # Returned as written. The document gave no currency here, and
        # prefixing "Rs." would put words in its mouth on a dollar invoice.
        return raw
    return None


def _percent(segment_text: str, offset: int = 0) -> Optional[str]:
    return dates.find_percent_after(segment_text, offset)


def _duration(segment_text: str, offset: int = 0) -> Optional[str]:
    return dates.find_duration_after(segment_text, offset)


def _date(segment_text: str, offset: int = 0) -> Optional[str]:
    iso, raw, _conf = dates.parse_date_after(segment_text, offset)
    return raw if iso else None


def _sentence(segment_text: str, offset: int = 0) -> Optional[str]:
    return truncate(segment_text, 220)


_REFERENCE = re.compile(
    r"(?:ref(?:erence)?|notice|file|bill|invoice|uhid|ip|account|policy|tender|nit|"
    r"bid|order|p\.?\s*o\.?|purchase\s+order|licence|license|registration|"
    r"certificate|case|arn|din|proj(?:ect)?|plan|cin)\s*"
    r"(?:no\.?|number|#|id)?\s*[:\-.]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9/\-.]{2,30}[A-Za-z0-9])",
    re.IGNORECASE,
)


def _reference(segment_text: str, offset: int = 0) -> Optional[str]:
    """An identifier following a reference label.

    The label is searched from the trigger onwards first, so "Invoice no: 12345
    against PO no: 88" yields 12345 for the invoice field and 88 for the PO
    field rather than both reading the first number on the line.
    """
    for window in (segment_text[max(0, offset - 30):], segment_text):
        for match in _REFERENCE.finditer(window):
            value = match.group(1)
            # A reference holds a digit. "Invoice to: Ketut" is not one.
            if any(ch.isdigit() for ch in value):
                return value
    return None


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

def _gstin(segment_text: str, offset: int = 0) -> Optional[str]:
    """A GSTIN is a fixed 15-character shape, so it can be matched exactly."""
    match = re.search(
        r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9])\b", segment_text.upper()
    )
    return match.group(1) if match else None


def _party_name(segment_text: str, offset: int = 0) -> Optional[str]:
    """The business name following a "Bill to" / "Supplier" style label."""
    window = segment_text[offset : offset + 160] if offset else segment_text
    window = window.lstrip(" :\t-–")
    match = re.search(
        r"([A-Z][A-Za-z.&'()\-]*(?:\s+[A-Z0-9][A-Za-z.&'()\-]*){0,6}"
        r"(?:\s+(?:Pvt|Private|Ltd|Limited|LLP|Inc|Corporation|Industries|Traders|"
        r"Enterprises|Agency|Agencies|Associates|Company|Co|Services|Solutions|Stores))?)",
        window,
    )
    if match and len(match.group(1).strip()) >= 3:
        return truncate(match.group(1).strip(), 80)
    first_line = window.strip().splitlines()[0] if window.strip() else ""
    return truncate(first_line, 80) or None


SPECS_BY_TYPE: Dict[str, List[Spec]] = {
    "invoice": [
        {
            "key": "invoice_number",
            "label": "Invoice number",
            "triggers": ["invoice no", "invoice number", "invoice #", "bill no",
                         "ഇൻവോയ്സ് നമ്പർ"],
            "extract": _reference,
            "confidence": "high",
        },
        {
            "key": "invoice_date",
            "label": "Invoice date",
            "triggers": ["invoice date", "date of invoice", "bill date", "dated"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "due_date",
            "label": "Payment due date",
            "triggers": ["due date", "payment due", "payable by", "payable on or before",
                         "pay by", "net 30", "net 15", "net 45"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "seller",
            "label": "Seller / supplier",
            "triggers": ["sold by", "supplier", "seller", "from:", "billed by",
                         "vendor"],
            "extract": _party_name,
            "confidence": "medium",
        },
        {
            "key": "buyer",
            "label": "Buyer / bill to",
            "triggers": ["bill to", "billed to", "invoice to", "buyer", "sold to",
                         "customer name", "ship to"],
            "extract": _party_name,
            "confidence": "medium",
        },
        {
            "key": "gstin",
            "label": "GSTIN",
            "triggers": ["gstin", "gst no", "gst number", "gst reg"],
            "extract": _gstin,
            "confidence": "high",
        },
        {
            "key": "subtotal",
            "label": "Subtotal",
            "triggers": ["sub total", "subtotal", "taxable value", "taxable amount",
                         "total before tax", "amount before tax", "net amount"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "discount",
            "label": "Discount",
            "triggers": ["discount", "less discount", "trade discount", "rebate"],
            "extract": _amount_percent_or_sentence,
            "confidence": "medium",
        },
        {
            "key": "cgst",
            "label": "CGST",
            "triggers": ["cgst"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "sgst",
            "label": "SGST",
            "triggers": ["sgst", "utgst"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "igst",
            "label": "IGST",
            "triggers": ["igst"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "tax_rate",
            "label": "Tax rate",
            "triggers": ["tax", "gst @", "gst@", "vat", "gst rate"],
            "extract": _percent,
            "confidence": "medium",
        },
        {
            "key": "tax_total",
            "label": "Tax charged",
            "triggers": ["total tax", "tax amount", "total gst", "gst amount", "vat",
                         "service tax", "tax"],
            "extract": _money,
            "confidence": "medium",
        },
        {
            "key": "other_charges",
            "label": "Other charges",
            "triggers": ["freight", "shipping", "packing", "handling", "delivery charge",
                         "transport charge", "insurance charge", "round off",
                         "rounded off"],
            "extract": _money,
            "confidence": "medium",
        },
        {
            "key": "total_amount",
            "label": "Invoice total",
            "triggers": ["grand total", "total amount", "net payable", "amount payable",
                         "total payable", "invoice total", "balance due", "amount due",
                         "ആകെ തുക"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "amount_in_words",
            "label": "Amount in words",
            "triggers": ["amount in words", "rupees in words", "in words"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "po_reference",
            "label": "Purchase order reference",
            "triggers": ["po no", "p.o. no", "purchase order no", "order reference",
                         "against po", "your order"],
            "extract": _reference,
            "confidence": "high",
        },
        {
            "key": "payment_terms",
            "label": "Payment terms",
            "triggers": ["payment terms", "terms of payment", "term and conditions",
                         "terms and conditions", "please send payment", "send payment within",
                         "payment within"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "payment_status",
            "label": "Payment status",
            "triggers": ["paid", "unpaid", "outstanding", "balance due", "advance received",
                         "payment received"],
            "extract": _sentence,
            "confidence": "low",
        },
    ],
    "purchase_order": [
        {
            "key": "po_number",
            "label": "Purchase order number",
            "triggers": ["purchase order no", "po no", "p.o. no", "order no",
                         "po number"],
            "extract": _reference,
            "confidence": "high",
        },
        {
            "key": "po_date",
            "label": "Order date",
            "triggers": ["po date", "order date", "date of order", "dated"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "seller",
            "label": "Supplier / vendor",
            "triggers": ["supplier", "vendor", "to m/s", "messrs", "seller"],
            "extract": _party_name,
            "confidence": "medium",
        },
        {
            "key": "buyer",
            "label": "Buyer",
            "triggers": ["bill to", "buyer", "ship to", "deliver to", "purchaser"],
            "extract": _party_name,
            "confidence": "medium",
        },
        {
            "key": "delivery_date",
            "label": "Delivery date",
            "triggers": ["delivery date", "deliver by", "delivery schedule",
                         "required by", "delivery on or before"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "total_amount",
            "label": "Order value",
            "triggers": ["grand total", "total value", "order value", "total amount",
                         "net payable"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "payment_terms",
            "label": "Payment terms",
            "triggers": ["payment terms", "terms of payment", "credit period"],
            "extract": _sentence,
            "confidence": "medium",
        },
    ],
    "tender": [
        {
            "key": "tender_title",
            "label": "Tender / name of work",
            "triggers": ["name of work", "tender for", "subject:", "work:",
                         "description of work"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "tender_reference",
            "label": "Tender reference",
            "triggers": ["tender no", "nit no", "tender reference", "bid no",
                         "tender id", "reference no"],
            "extract": _reference,
            "confidence": "high",
        },
        {
            "key": "authority",
            "label": "Issuing authority",
            "triggers": ["tender inviting authority", "department", "corporation",
                         "panchayat", "authority", "office of the", "municipality"],
            "extract": _authority,
            "confidence": "medium",
        },
        {
            "key": "estimate_value",
            "label": "Estimated value (PAC)",
            "triggers": ["estimate pac", "estimated cost", "estimate amount",
                         "probable amount of contract", "pac"],
            "extract": _money,
            "confidence": "medium",
        },
        {
            "key": "emd",
            "label": "EMD / bid security",
            "triggers": ["earnest money", "emd", "bid security"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "tender_fee",
            "label": "Tender fee",
            "triggers": ["tender fee", "tender submission fee", "cost of tender document",
                         "document fee"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "performance_security",
            "label": "Performance security",
            "triggers": ["performance security", "performance guarantee",
                         "security deposit"],
            "extract": _amount_percent_or_sentence,
            "confidence": "medium",
        },
        {
            "key": "submission_deadline",
            "label": "Bid submission closing",
            "triggers": ["bid submission closing", "last date for submission",
                         "submission closing date", "due date and time of submission",
                         "online bid submission closing"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "opening_date",
            "label": "Bid opening",
            "triggers": ["date and time of opening", "bid opening", "tender opening",
                         "opening of online tender", "opening of bids"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "completion_period",
            "label": "Period of completion",
            "triggers": ["period of completion", "completion period", "contract period",
                         "time of completion"],
            "extract": _duration,
            "confidence": "high",
        },
        {
            "key": "bidder_class",
            "label": "Classification of bidder",
            "triggers": ["classification of bidder", "class of contractor",
                         "category of bidder", "eligible class"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "turnover_requirement",
            "label": "Turnover requirement",
            "triggers": ["annual turnover", "average turnover", "minimum turnover",
                         "turnover of"],
            "extract": _amount_percent_or_sentence,
            "confidence": "medium",
        },
        {
            "key": "experience_requirement",
            "label": "Experience requirement",
            "triggers": ["similar work", "experience of", "years of experience",
                         "completed works"],
            "extract": _sentence,
            "confidence": "medium",
        },
    ],
    "gst_notice": [
        {
            "key": "notice_type",
            "label": "Notice type / form",
            "triggers": ["form gst", "drc-01", "drc-07", "asmt-10", "reg-17",
                         "notice under section", "show cause notice"],
            "extract": _sentence,
            "confidence": "high",
        },
        {
            "key": "reference",
            "label": "Reference number",
            "triggers": ["reference no", "ref no", "notice no", "arn", "din",
                         "case id"],
            "extract": _reference,
            "confidence": "high",
        },
        {
            "key": "authority",
            "label": "Issuing authority",
            "triggers": ["state tax officer", "commissioner", "superintendent",
                         "department", "office of the", "proper officer"],
            "extract": _authority,
            "confidence": "medium",
        },
        {
            "key": "gstin",
            "label": "GSTIN",
            "triggers": ["gstin", "gst no", "gst registration"],
            "extract": _gstin,
            "confidence": "high",
        },
        {
            "key": "tax_period",
            "label": "Tax period",
            "triggers": ["tax period", "period:", "financial year", "for the period",
                         "assessment year"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "tax_amount",
            "label": "Tax demanded",
            "triggers": ["tax amount", "tax payable", "tax due", "amount of tax"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "interest_amount",
            "label": "Interest",
            "triggers": ["interest amount", "interest payable", "interest under section",
                         "interest"],
            "extract": _money,
            "confidence": "medium",
        },
        {
            "key": "penalty_amount",
            "label": "Penalty",
            "triggers": ["penalty amount", "penalty payable", "penalty under section",
                         "penalty"],
            "extract": _money,
            "confidence": "medium",
        },
        {
            "key": "total_amount",
            "label": "Total demanded",
            "triggers": ["total amount", "grand total", "total payable", "total demand",
                         "aggregate amount"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "deadline",
            "label": "Response deadline",
            "triggers": ["on or before", "within", "failing which", "last date",
                         "not later than", "reply by", "respond by"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "documents_requested",
            "label": "Documents requested",
            "triggers": ["documents required", "furnish the following", "produce the",
                         "submit the following", "along with the following"],
            "extract": _sentence,
            "confidence": "medium",
        },
    ],
    "contract": [
        {
            "key": "parties",
            "label": "Parties",
            "triggers": ["between", "party of the first part", "this agreement is made",
                         "by and between"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "effective_date",
            "label": "Effective date",
            "triggers": ["effective from", "with effect from", "commences on",
                         "effective date", "shall commence"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "duration",
            "label": "Contract duration",
            "triggers": ["term of", "period of", "duration of", "for a term",
                         "valid for"],
            "extract": _duration,
            "confidence": "medium",
        },
        {
            "key": "end_date",
            "label": "End date",
            "triggers": ["expire", "expiry", "end date", "terminate on", "valid upto",
                         "valid up to", "until"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "contract_value",
            "label": "Contract value",
            "triggers": ["contract value", "total consideration", "fees payable",
                         "service charge", "annual fee", "total value"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "notice_period",
            "label": "Termination notice period",
            "triggers": ["notice period", "months notice", "days notice",
                         "written notice of", "prior notice"],
            "extract": _duration,
            "confidence": "high",
        },
        {
            "key": "renewal",
            "label": "Renewal condition",
            "triggers": ["renew", "renewal", "automatically renewed",
                         "extended for a further"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "payment_terms",
            "label": "Payment terms",
            "triggers": ["payment terms", "shall be paid within", "invoice shall be",
                         "credit period"],
            "extract": _sentence,
            "confidence": "medium",
        },
    ],
    "insurance": [
        {
            "key": "policy_number",
            "label": "Policy number",
            "triggers": ["policy no", "policy number", "certificate no"],
            "extract": _reference,
            "confidence": "high",
        },
        {
            "key": "policy_type",
            "label": "Policy type",
            "triggers": ["policy type", "type of policy", "product name", "plan name",
                         "health insurance", "motor insurance", "life insurance"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "sum_insured",
            "label": "Sum insured",
            "triggers": ["sum insured", "sum assured", "coverage amount",
                         "total coverage"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "premium",
            "label": "Premium",
            "triggers": ["premium", "total premium", "annual premium",
                         "പ്രീമിയം"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "policy_period",
            "label": "Policy period",
            "triggers": ["policy period", "period of insurance", "valid from",
                         "policy term"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "expiry_date",
            "label": "Expiry / renewal date",
            "triggers": ["expiry date", "expires on", "valid upto", "valid up to",
                         "renewal date", "due for renewal"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "waiting_period",
            "label": "Waiting period",
            "triggers": ["waiting period", "initial waiting", "cooling period"],
            "extract": _duration,
            "confidence": "high",
        },
        {
            "key": "deductible",
            "label": "Deductible",
            "triggers": ["deductible", "excess of", "franchise"],
            "extract": _amount_percent_or_sentence,
            "confidence": "high",
        },
        {
            "key": "copayment",
            "label": "Co-payment",
            "triggers": ["co-payment", "copayment", "co payment", "copay"],
            "extract": _amount_percent_or_sentence,
            "confidence": "high",
        },
        {
            "key": "exclusions",
            "label": "Exclusions",
            "triggers": ["exclusions", "not covered", "shall not cover",
                         "excluded from"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "claim_deadline",
            "label": "Claim intimation deadline",
            "triggers": ["claim intimation", "intimate the claim", "notify the company within",
                         "claim must be"],
            "extract": _sentence,
            "confidence": "high",
        },
    ],
    "financial_statement": [
        {
            "key": "period",
            "label": "Period covered",
            "triggers": ["for the year ended", "as at", "as on", "period from",
                         "financial year"],
            "extract": _sentence,
            "confidence": "high",
        },
        {
            "key": "turnover",
            "label": "Turnover / revenue",
            "triggers": ["revenue from operations", "total revenue", "turnover",
                         "total income", "sales"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "profit",
            "label": "Profit / loss",
            "triggers": ["profit for the year", "net profit", "profit before tax",
                         "net loss", "profit after tax"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "total_assets",
            "label": "Total assets",
            "triggers": ["total assets", "total of assets"],
            "extract": _money,
            "confidence": "high",
        },
        {
            "key": "closing_balance",
            "label": "Closing balance",
            "triggers": ["closing balance", "balance carried", "balance as on"],
            "extract": _money,
            "confidence": "medium",
        },
    ],
    "business_license": [
        {
            "key": "licence_number",
            "label": "Licence / registration number",
            "triggers": ["licence no", "license no", "registration no", "udyam registration",
                         "certificate no", "cin"],
            "extract": _reference,
            "confidence": "high",
        },
        {
            "key": "holder",
            "label": "Issued to",
            "triggers": ["issued to", "name of enterprise", "name of the establishment",
                         "proprietor", "business name"],
            "extract": _party_name,
            "confidence": "medium",
        },
        {
            "key": "authority",
            "label": "Issuing authority",
            "triggers": ["department", "corporation", "panchayat", "authority",
                         "municipality", "office of the"],
            "extract": _authority,
            "confidence": "medium",
        },
        {
            "key": "issue_date",
            "label": "Date of issue",
            "triggers": ["date of issue", "issued on", "dated", "date of registration"],
            "extract": _date,
            "confidence": "high",
        },
        {
            "key": "expiry_date",
            "label": "Valid until",
            "triggers": ["valid until", "valid upto", "valid up to", "expires on",
                         "expiry date", "renewal due"],
            "extract": _date,
            "confidence": "high",
        },
    ],
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
    "legal_notice": [
        {
            "key": "notice_date",
            "label": "Notice date",
            "triggers": ["dated", "date:", "notice date"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "sender",
            "label": "Sent on behalf of",
            "triggers": ["on behalf of my client", "on behalf of", "my client"],
            "extract": _party_name,
            "confidence": "low",
        },
        {
            "key": "subject",
            "label": "Subject",
            "triggers": ["subject:", "sub:", "sub :", "re:", "notice under section",
                         "notice to quit"],
            "extract": _sentence,
            "confidence": "medium",
        },
        {
            "key": "amount_demanded",
            "label": "Amount demanded",
            "triggers": ["call upon you to pay", "amount of rs", "sum of rs", "due and outstanding",
                         "outstanding amount", "pay rs", "an amount of"],
            "extract": _money,
            "confidence": "medium",
        },
        {
            "key": "reference",
            "label": "Reference / account number",
            "triggers": ["ref. no", "ref no", "reference no", "account no", "loan account",
                         "cheque no"],
            "extract": _reference,
            "confidence": "medium",
        },
        {
            "key": "response_window",
            "label": "Time given to respond",
            "triggers": ["within", "days of receipt", "from the receipt"],
            "extract": _duration,
            "confidence": "medium",
        },
        {
            "key": "deadline",
            "label": "Response deadline",
            "triggers": ["on or before", "failing which", "not later than", "last date"],
            "extract": _date,
            "confidence": "medium",
        },
        {
            "key": "consequence",
            "label": "Stated consequence",
            "triggers": ["failing which", "legal proceedings", "constrained to",
                         "at your own risk and cost", "civil and criminal"],
            "extract": _sentence,
            "confidence": "medium",
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

    # Invoice templates often print the date with no label, next to the
    # buyer's name ("Ketut Susilo   25 June 2022"). When no labelled invoice
    # date exists, the first full date near the top of the document is taken,
    # marked uncertain so the user confirms it.
    if doc_type in ("invoice", "purchase_order") and "invoice_date" not in found \
            and "po_date" not in found:
        for segment in segments[:12]:
            iso, raw, _conf = dates.parse_date(segment.text)
            if iso and raw:
                key = "invoice_date" if doc_type == "invoice" else "po_date"
                found[key] = Fact(
                    key=key,
                    label="Invoice date" if doc_type == "invoice" else "Order date",
                    value=raw,
                    page=segment.page,
                    source_text=truncate(segment.text, 300),
                    confidence="low",
                    uncertain=True,
                    evidence_status="needs_verification",
                )
                break

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
