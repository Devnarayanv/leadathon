"""Financial verification engine.

Every check here re-does the document's own arithmetic from the figures the
document states, and reports the formula, the inputs, the document's answer,
Doc Decode's answer and the difference. Nothing is estimated and no missing
figure is filled in: a check whose inputs are not all present is reported as
"missing information", never computed from a guess.

All arithmetic is Decimal (see money.py).

OCR is the one source of doubt that arithmetic cannot remove. A "3" read where
the page prints a "9" produces a perfectly computed mismatch that does not
exist on paper. So when the figures came from OCR, a mismatch is reported as
"needs attention" with an instruction to compare against the original, rather
than as a confirmed error.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import money
from schemas import Fact, LineItem, VerificationCheck, VerificationReport

TOLERANCE = Decimal("1.00")

KIND_LABELS = {
    "invoice": "Invoice arithmetic",
    "purchase_order": "Purchase order arithmetic",
    "hospital_bill": "Bill arithmetic",
    "loan": "Loan repayment calculation",
    "gst_notice": "Demand total",
    "tender": "Tender deposits",
    "rental": "Rent and deposit",
    "insurance": "Premium and cover",
}


class _Facts:
    """Fact lookup that remembers which inputs a check actually used."""

    def __init__(self, facts: List[Fact]):
        self.by_key: Dict[str, Fact] = {f.key: f for f in facts}

    def fact(self, key: str) -> Optional[Fact]:
        return self.by_key.get(key)

    def amount(self, key: str) -> Optional[Decimal]:
        fact = self.by_key.get(key)
        return money.parse(fact.value) if fact else None

    def percent(self, key: str) -> Optional[Decimal]:
        fact = self.by_key.get(key)
        return money.parse_percent(fact.value) if fact else None

    def label(self, key: str, fallback: str) -> str:
        fact = self.by_key.get(key)
        return fact.label if fact else fallback


def _num(value: Decimal) -> str:
    """A plain decimal for display: 10 not 1E+1, 2.5 not 2.50."""
    text = format(value.normalize(), "f")
    return text


def _input(label: str, value: Optional[Decimal], currency: str, source: str = "extracted",
           page: Optional[int] = None, percent: bool = False) -> Dict[str, str]:
    if value is None:
        shown = "Not stated"
    elif percent:
        shown = "%s%%" % _num(value)
    else:
        shown = money.fmt(value, currency)
    entry = {"label": label, "value": shown, "source": source}
    if page is not None:
        entry["page"] = str(page)
    return entry


def _compare(document: Decimal, calculated: Decimal, ocr: bool) -> Tuple[str, Decimal]:
    difference = money.q(document - calculated)
    if abs(difference) <= TOLERANCE:
        return "verified", difference
    return ("needs_attention" if ocr else "mismatch"), difference


def _difference_text(difference: Decimal, currency: str) -> str:
    if difference == 0:
        return money.fmt(Decimal(0), currency)
    sign = "+" if difference > 0 else "−"
    return "%s%s" % (sign, money.fmt(abs(difference), currency))


def _ocr_note(status: str) -> str:
    if status == "needs_attention":
        return (
            " The figures were read by OCR, which can misread a single digit "
            "(a 3 for a 9, a 1 for a 7). Compare these numbers with the original "
            "before treating this as an error."
        )
    return ""


# ---------------------------------------------------------------------------
# Invoice / bill / purchase order
# ---------------------------------------------------------------------------

def _line_item_checks(items: List[LineItem], currency: str, ocr: bool,
                      subtotal: Optional[Decimal]) -> Tuple[List[VerificationCheck], Optional[Decimal], bool]:
    """Per-row quantity x rate checks, and the sum of the rows.

    Returns (checks, sum_of_rows, rows_are_trustworthy). On an OCR'd document
    the rows are only trusted when they add up to the stated subtotal: a table
    that OCR has mangled produces a column of fake mismatches, which would be
    the worst possible thing to put in front of a user.
    """
    rows = []
    for item in items:
        qty = money.parse(item.quantity) if item.quantity else None
        rate = money.parse(item.unit_price) if item.unit_price else None
        amount = money.parse(item.amount) if item.amount else None
        rows.append((item, qty, rate, amount))

    stated_sum = sum((r[3] for r in rows if r[3] is not None), Decimal(0))
    if not rows:
        return [], None, False

    trustworthy = True
    if ocr:
        trustworthy = subtotal is not None and money.within_tolerance(stated_sum, subtotal, TOLERANCE)

    if not trustworthy:
        check = VerificationCheck(
            key="line_items_unreadable",
            label="Line items",
            status="unable_to_verify",
            formula="Σ (quantity × unit price)",
            explanation=(
                "%d table row(s) were read from the scan, but they do not add up to "
                "the stated subtotal, which usually means OCR misread the table "
                "rather than that the invoice is wrong. Line-by-line arithmetic was "
                "not checked. Upload a clearer scan or the original PDF to verify "
                "each row." % len(rows)
            ),
            assumptions=["Row figures read by OCR were not trusted for arithmetic."],
        )
        return [check], None, False

    checks: List[VerificationCheck] = []
    for index, (item, qty, rate, amount) in enumerate(rows, start=1):
        if qty is None or rate is None or amount is None:
            continue
        calculated = money.q(qty * rate)
        status, difference = _compare(amount, calculated, ocr)
        checks.append(
            VerificationCheck(
                key="line_%d" % index,
                label=item.description or "Row %d" % index,
                status=status,
                formula="%s × %s" % (_num(qty), money.fmt(rate, currency)),
                inputs=[
                    _input("Quantity", qty, "", page=item.page) | {"value": str(_num(qty))},
                    _input("Unit price", rate, currency, page=item.page),
                ],
                document_value=money.fmt(amount, currency),
                calculated_value=money.fmt(calculated, currency),
                difference=_difference_text(difference, currency),
                explanation=(
                    "Row total matches quantity × unit price."
                    if status == "verified"
                    else "The row total on the document is %s, but %s × %s = %s."
                    % (money.fmt(amount, currency), _num(qty),
                       money.fmt(rate, currency), money.fmt(calculated, currency))
                    + _ocr_note(status)
                ),
                page=item.page,
                source_text=item.source_text,
            )
        )
    # The subtotal is checked against the row totals AS PRINTED, not against
    # recomputed qty x rate. Otherwise one wrong row cascades into a "wrong"
    # subtotal, a "wrong" tax and a "wrong" total, and the user is shown four
    # errors where the document has one. Each check isolates one step.
    return checks, stated_sum, True


def _corrected_bill(items: List[LineItem], row_checks: List[VerificationCheck],
                    subtotal: Optional[Decimal], discount: Optional[Decimal],
                    other: Optional[Decimal], tax_total: Optional[Decimal],
                    tax_rate: Optional[Decimal], total: Optional[Decimal],
                    currency: str) -> Optional[VerificationCheck]:
    wrong = [c for c in row_checks if c.key.startswith("line_") and c.status == "mismatch"]
    if not wrong or total is None:
        return None
    if tax_total is not None and tax_rate is None:
        return None  # tax is charged but its rate is unknown: cannot recompute it honestly

    rows_sum = Decimal(0)
    for item in items:
        qty = money.parse(item.quantity) if item.quantity else None
        rate = money.parse(item.unit_price) if item.unit_price else None
        amount = money.parse(item.amount) if item.amount else None
        if qty is not None and rate is not None:
            rows_sum += money.q(qty * rate)
        elif amount is not None:
            rows_sum += amount
        else:
            return None

    base = rows_sum - (discount or Decimal(0))
    gst = money.pct_of(base, tax_rate) if tax_rate is not None else Decimal(0)
    correct_total = base + gst + (other or Decimal(0))
    overcharge = money.q(total - correct_total)

    inputs = [_input("Corrected subtotal", rows_sum, currency, source="calculated")]
    parts = [money.fmt(rows_sum, currency)]
    if discount:
        inputs.append(_input("Discount", discount, currency))
        parts.append("− " + money.fmt(discount, currency))
    if tax_rate is not None:
        inputs.append(_input("GST at %s%%" % _num(tax_rate), gst, currency, source="calculated"))
        parts.append("+ " + money.fmt(gst, currency))
    if other:
        inputs.append(_input("Other charges", other, currency))
        parts.append("+ " + money.fmt(other, currency))

    rows_text = ", ".join(c.label for c in wrong)
    if overcharge > 0:
        verdict = "You are being asked for %s more than you owe." % money.fmt(overcharge, currency)
    elif overcharge < 0:
        verdict = "The document asks for %s less than the correct amount." % money.fmt(-overcharge, currency)
    else:
        verdict = "The total is unaffected."
    gst_text = (" GST at %s%% on %s is %s%s." % (
        _num(tax_rate), money.fmt(base, currency), money.fmt(gst, currency),
        "" if tax_total is None else " (the document charges %s)" % money.fmt(tax_total, currency))
        if tax_rate is not None else "")
    return VerificationCheck(
        key="corrected_total",
        label="Correct amount payable",
        status="needs_attention",
        formula=" ".join(parts),
        inputs=inputs,
        document_value=money.fmt(total, currency),
        calculated_value=money.fmt(correct_total, currency),
        difference=_difference_text(overcharge, currency),
        explanation=(
            "With %s corrected to quantity × rate, the subtotal is %s.%s The correct total is %s, "
            "but the document asks for %s. %s"
            % (rows_text, money.fmt(rows_sum, currency), gst_text,
               money.fmt(correct_total, currency), money.fmt(total, currency), verdict)
        ),
        assumptions=["Every row recomputed as quantity × unit price; the stated GST rate applied to the result."],
    )


def verify_invoice(facts: List[Fact], items: List[LineItem], currency: str,
                   ocr: bool, kind: str = "invoice") -> VerificationReport:
    f = _Facts(facts)
    checks: List[VerificationCheck] = []
    assumptions: List[str] = []
    missing: List[str] = []

    subtotal = f.amount("subtotal")
    # Extractors name the same figure differently per document type (a PO's
    # "Total:" arrives as "total", an invoice's "Grand Total:" as
    # "total_amount"), so take whichever the document actually gave.
    total_key = "total_amount" if f.fact("total_amount") else "total"
    total = f.amount(total_key)
    tax_total = f.amount("tax_total")
    cgst, sgst, igst = f.amount("cgst"), f.amount("sgst"), f.amount("igst")
    cgst_rate, sgst_rate = f.percent("cgst_rate"), f.percent("sgst_rate")
    igst_rate = f.percent("igst_rate")
    rate_from_halves = False
    if cgst_rate is not None and sgst_rate is not None:
        # "CGST @ 9%" + "SGST @ 9%": the GST rate is the sum of the halves.
        tax_rate = cgst_rate + sgst_rate
        rate_from_halves = True
    elif igst_rate is not None:
        tax_rate = igst_rate
    else:
        tax_rate = f.percent("tax_rate")
    discount_fact = f.fact("discount")
    discount = money.parse(discount_fact.value) if discount_fact and "%" not in discount_fact.value else None
    other = f.amount("other_charges")

    # 1. Rows
    row_checks, rows_sum, rows_ok = _line_item_checks(items, currency, ocr, subtotal)
    checks.extend(row_checks)

    # 2. Rows add up to the subtotal
    if rows_ok and rows_sum is not None and subtotal is not None:
        status, difference = _compare(subtotal, rows_sum, ocr)
        checks.append(
            VerificationCheck(
                key="subtotal",
                label="Subtotal",
                status=status,
                formula="Σ line totals (%d rows)" % len([c for c in row_checks if c.key.startswith("line_")]),
                inputs=[_input("Sum of rows", rows_sum, currency, source="calculated")],
                document_value=money.fmt(subtotal, currency),
                calculated_value=money.fmt(rows_sum, currency),
                difference=_difference_text(difference, currency),
                explanation=(
                    "The subtotal equals the sum of the line items."
                    if status == "verified"
                    else "The line items add up to %s, but the invoice states a subtotal of %s."
                    % (money.fmt(rows_sum, currency), money.fmt(subtotal, currency))
                    + _ocr_note(status)
                ),
                page=f.fact("subtotal").page if f.fact("subtotal") else None,
                source_text=f.fact("subtotal").source_text if f.fact("subtotal") else None,
            )
        )
    if subtotal is None and rows_ok and rows_sum is not None:
        # No stated subtotal: the rows' own sum becomes the base, and the
        # report says so rather than pretending the document gave it.
        subtotal = rows_sum
        assumptions.append(
            "The invoice states no subtotal, so the sum of the line items (%s) was used as the taxable base."
            % money.fmt(rows_sum, currency)
        )

    # 3. Split GST adds up
    if cgst is not None and sgst is not None:
        split = cgst + sgst
        if tax_total is not None:
            status, difference = _compare(tax_total, split, ocr)
            checks.append(
                VerificationCheck(
                    key="gst_split",
                    label="CGST + SGST",
                    status=status,
                    formula="CGST + SGST",
                    inputs=[_input("CGST", cgst, currency), _input("SGST", sgst, currency)],
                    document_value=money.fmt(tax_total, currency),
                    calculated_value=money.fmt(split, currency),
                    difference=_difference_text(difference, currency),
                    explanation=(
                        "CGST and SGST add up to the tax charged."
                        if status == "verified"
                        else "CGST + SGST = %s, but the tax charged is %s." % (
                            money.fmt(split, currency), money.fmt(tax_total, currency))
                        + _ocr_note(status)
                    ),
                )
            )
        else:
            tax_total = split
        if not money.within_tolerance(cgst, sgst, TOLERANCE):
            checks.append(
                VerificationCheck(
                    key="gst_halves",
                    label="CGST equals SGST",
                    status="needs_attention",
                    formula="CGST = SGST",
                    inputs=[_input("CGST", cgst, currency), _input("SGST", sgst, currency)],
                    document_value=money.fmt(cgst, currency),
                    calculated_value=money.fmt(sgst, currency),
                    difference=_difference_text(cgst - sgst, currency),
                    explanation=(
                        "On an intra-state supply CGST and SGST are normally equal halves "
                        "of the GST. They differ here; ask the supplier why."
                    ),
                )
            )
    elif igst is not None and tax_total is None:
        tax_total = igst

    # 4. Tax = base x rate
    # "CGST @ 9%" and "SGST @ 9%" state the rate of each half. The GST rate is
    # their sum, and checking the combined tax against 9% would report a false
    # mismatch on every correct intra-state invoice.
    rate_fact = f.fact("tax_rate")
    if rate_from_halves:
        assumptions.append(
            "CGST %s%% + SGST %s%% = GST %s%%." % (_num(cgst_rate), _num(sgst_rate), _num(tax_rate))
        )
    elif (tax_rate is not None and cgst is not None and sgst is not None and rate_fact
            and any(w in (rate_fact.source_text or "").lower() for w in ("cgst", "sgst", "utgst"))):
        assumptions.append(
            "The %s%% rate is stated per half (CGST and SGST each), so the GST rate checked is %s%%."
            % (_num(tax_rate), _num(tax_rate * 2))
        )
        tax_rate = tax_rate * 2
    if subtotal is not None and tax_rate is not None and tax_total is not None:
        base = subtotal - (discount or Decimal(0))
        calculated_tax = money.pct_of(base, tax_rate)
        status, difference = _compare(tax_total, calculated_tax, ocr)
        tax_fact = f.fact("tax_total")
        checks.append(
            VerificationCheck(
                key="tax",
                label="Tax at %s%%" % _num(tax_rate),
                status=status,
                formula="%s × %s%%" % (money.fmt(base, currency), _num(tax_rate)),
                inputs=[
                    _input("Taxable base", base, currency,
                           source="calculated" if discount else "extracted"),
                    _input("Tax rate", tax_rate, currency, percent=True),
                ],
                document_value=money.fmt(tax_total, currency),
                calculated_value=money.fmt(calculated_tax, currency),
                difference=_difference_text(difference, currency),
                explanation=(
                    "Tax matches the stated rate applied to the taxable base"
                    + (" (within rounding)." if difference != 0 else ".")
                    if status == "verified"
                    else "%s%% of %s is %s, but the invoice charges %s in tax." % (
                        _num(tax_rate), money.fmt(base, currency),
                        money.fmt(calculated_tax, currency), money.fmt(tax_total, currency))
                    + _ocr_note(status)
                ),
                page=tax_fact.page if tax_fact else None,
                source_text=tax_fact.source_text if tax_fact else None,
                assumptions=(["Rounded to the nearest paisa, half up."] if difference != 0 else []),
            )
        )

    # 5. Grand total
    if total is not None and subtotal is not None:
        calculated_total = subtotal - (discount or Decimal(0)) + (tax_total or Decimal(0)) + (other or Decimal(0))
        parts = [money.fmt(subtotal, currency)]
        inputs = [_input("Subtotal", subtotal, currency,
                         source="extracted" if f.fact("subtotal") else "calculated")]
        if discount:
            parts.append("− " + money.fmt(discount, currency))
            inputs.append(_input("Discount", discount, currency))
        if tax_total is not None:
            parts.append("+ " + money.fmt(tax_total, currency))
            inputs.append(_input("Tax", tax_total, currency))
        if other:
            parts.append("+ " + money.fmt(other, currency))
            inputs.append(_input("Other charges", other, currency))
        status, difference = _compare(total, calculated_total, ocr)
        total_fact = f.fact(total_key)
        if tax_total is None:
            assumptions.append("No tax line was found, so the total was checked as subtotal only.")
        checks.append(
            VerificationCheck(
                key="grand_total",
                label="Grand total",
                status=status,
                formula=" ".join(parts),
                inputs=inputs,
                document_value=money.fmt(total, currency),
                calculated_value=money.fmt(calculated_total, currency),
                difference=_difference_text(difference, currency),
                explanation=(
                    "The grand total equals subtotal%s%s."
                    % (" − discount" if discount else "", " + tax" if tax_total is not None else "")
                    if status == "verified"
                    else "The invoice total is %s, but %s = %s. %s %s."
                    % (
                        money.fmt(total, currency),
                        " ".join(parts),
                        money.fmt(calculated_total, currency),
                        "The invoice asks for" if difference > 0 else "The invoice asks for",
                        ("%s more than its own figures add up to" if difference > 0
                         else "%s less than its own figures add up to")
                        % money.fmt(abs(difference), currency),
                    )
                    + _ocr_note(status)
                ),
                page=total_fact.page if total_fact else None,
                source_text=total_fact.source_text if total_fact else None,
            )
        )

    # 6. What the bill should be. The checks above isolate each step, so a
    # wrong row shows as one error. This works out the knock-on effect: the
    # subtotal, GST and total the document would carry with that row fixed.
    # Only for confirmed row errors: an OCR misread is not an overcharge.
    corrected = _corrected_bill(items, row_checks, subtotal, discount, other, tax_total,
                                tax_rate, total, currency)
    if corrected is not None:
        checks.append(corrected)

    for key, label in ((total_key, "Invoice total"), ("subtotal", "Subtotal"),
                       ("invoice_number", "Invoice number"), ("invoice_date", "Invoice date")):
        if kind == "invoice" and not f.fact(key) and not (key == "subtotal" and rows_ok):
            missing.append(label)
    if kind == "invoice" and tax_total is None and tax_rate is None:
        missing.append("Tax (GST) breakdown")

    return _finish(kind, checks, assumptions, missing)


# ---------------------------------------------------------------------------
# Loan
# ---------------------------------------------------------------------------

def _months(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    import dates

    days = dates.duration_days(text)
    if days is None:
        return None
    lowered = text.lower()
    if "year" in lowered:
        return int(round(days / 365 * 12))
    if "month" in lowered:
        return int(round(days / 30))
    return None


def emi(principal: Decimal, annual_rate_pct: Decimal, months: int) -> Decimal:
    """Standard reducing-balance EMI: P·r·(1+r)^n / ((1+r)^n − 1)."""
    if months <= 0:
        raise ValueError("months must be positive")
    r = annual_rate_pct / Decimal(1200)
    if r == 0:
        return money.q(principal / months)
    growth = (Decimal(1) + r) ** months
    return money.q(principal * r * growth / (growth - Decimal(1)))


def verify_loan(facts: List[Fact], currency: str, ocr: bool) -> VerificationReport:
    f = _Facts(facts)
    checks: List[VerificationCheck] = []
    assumptions: List[str] = []
    missing: List[str] = []

    principal = f.amount("loan_amount")
    rate = f.percent("interest_rate")
    months = _months(f.fact("repayment_duration").value if f.fact("repayment_duration") else None)
    stated_emi = f.amount("emi")

    for value, label in ((principal, "Loan amount"), (rate, "Interest rate"), (months, "Repayment duration")):
        if value is None:
            missing.append(label)

    if principal is not None and rate is not None and months:
        calculated = emi(principal, rate, months)
        assumptions.append(
            "Reducing-balance method with monthly compounding (r = annual rate ÷ 12). "
            "Flat-rate loans calculate EMI differently, and a different result is "
            "expected for them."
        )
        inputs = [
            _input("Principal (P)", principal, currency, page=f.fact("loan_amount").page),
            _input("Annual rate", rate, currency, percent=True, page=f.fact("interest_rate").page),
            {"label": "Months (n)", "value": str(months), "source": "extracted"},
        ]
        if stated_emi is not None:
            status, difference = _compare(stated_emi, calculated, ocr)
            # Lenders round EMI up to the rupee, and some charge on a
            # slightly different day count; a few rupees is not a finding.
            if status != "verified" and abs(difference) <= max(Decimal(5), calculated * Decimal("0.005")):
                status = "verified"
            checks.append(
                VerificationCheck(
                    key="emi",
                    label="EMI",
                    status=status,
                    formula="P × r × (1+r)ⁿ ÷ ((1+r)ⁿ − 1)",
                    inputs=inputs,
                    document_value=money.fmt(stated_emi, currency),
                    calculated_value=money.fmt(calculated, currency),
                    difference=_difference_text(difference, currency),
                    explanation=(
                        "The stated EMI matches the standard reducing-balance formula."
                        if status == "verified"
                        else "The standard formula gives %s per month, but the document states %s. "
                        "Ask the lender whether the rate is a flat rate or whether fees are "
                        "included in the EMI." % (money.fmt(calculated, currency), money.fmt(stated_emi, currency))
                        + _ocr_note(status)
                    ),
                    page=f.fact("emi").page,
                    source_text=f.fact("emi").source_text,
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    key="emi_calculated",
                    label="EMI (calculated)",
                    status="verified",
                    formula="P × r × (1+r)ⁿ ÷ ((1+r)ⁿ − 1)",
                    inputs=inputs,
                    calculated_value=money.fmt(calculated, currency),
                    explanation="The document states no EMI. This is what the stated loan terms imply.",
                )
            )
        monthly = stated_emi if stated_emi is not None else calculated
        total_repayment = money.q(monthly * months)
        interest = money.q(total_repayment - principal)
        checks.append(
            VerificationCheck(
                key="total_repayment",
                label="Total repayment",
                status="verified",
                formula="%s × %d months" % (money.fmt(monthly, currency), months),
                inputs=[
                    _input("EMI", monthly, currency,
                           source="extracted" if stated_emi is not None else "calculated"),
                    {"label": "Months", "value": str(months), "source": "extracted"},
                ],
                calculated_value=money.fmt(total_repayment, currency),
                explanation="You would repay %s in all, of which %s is interest (%s%% of the amount borrowed)."
                % (money.fmt(total_repayment, currency), money.fmt(interest, currency),
                   (interest / principal * 100).quantize(Decimal("0.1")) if principal else "—"),
            )
        )

    fee_fact = f.fact("processing_fee")
    if fee_fact and principal is not None:
        fee_pct = money.parse_percent(fee_fact.value)
        if fee_pct is not None:
            fee = money.pct_of(principal, fee_pct)
            checks.append(
                VerificationCheck(
                    key="processing_fee",
                    label="Processing fee",
                    status="verified",
                    formula="%s × %s%%" % (money.fmt(principal, currency), _num(fee_pct)),
                    inputs=[_input("Loan amount", principal, currency),
                            _input("Fee rate", fee_pct, currency, percent=True)],
                    calculated_value=money.fmt(fee, currency),
                    explanation="A one-time fee of %s, usually deducted from the amount paid out to you."
                    % money.fmt(fee, currency),
                    page=fee_fact.page,
                    source_text=fee_fact.source_text,
                    assumptions=["GST on the fee, if charged, is not included."],
                )
            )
    return _finish("loan", checks, assumptions, missing)


# ---------------------------------------------------------------------------
# GST notice, tender, rental, insurance
# ---------------------------------------------------------------------------

def verify_demand(facts: List[Fact], currency: str, ocr: bool) -> VerificationReport:
    f = _Facts(facts)
    checks: List[VerificationCheck] = []
    missing: List[str] = []
    tax, interest, penalty = f.amount("tax_amount"), f.amount("interest_amount"), f.amount("penalty_amount")
    total = f.amount("total_amount")
    parts = [(label, value) for label, value in (("Tax", tax), ("Interest", interest), ("Penalty", penalty)) if value is not None]
    if total is not None and len(parts) >= 2:
        calculated = sum((v for _, v in parts), Decimal(0))
        status, difference = _compare(total, calculated, ocr)
        checks.append(
            VerificationCheck(
                key="demand_total",
                label="Total demanded",
                status=status,
                formula=" + ".join(label for label, _ in parts),
                inputs=[_input(label, value, currency) for label, value in parts],
                document_value=money.fmt(total, currency),
                calculated_value=money.fmt(calculated, currency),
                difference=_difference_text(difference, currency),
                explanation=(
                    "The total demanded equals the components listed in the notice."
                    if status == "verified"
                    else "The components add up to %s, but the notice demands %s. Raise this in your reply."
                    % (money.fmt(calculated, currency), money.fmt(total, currency)) + _ocr_note(status)
                ),
                page=f.fact("total_amount").page,
                source_text=f.fact("total_amount").source_text,
            )
        )
    for key, label in (("tax_amount", "Tax demanded"), ("total_amount", "Total demanded")):
        if not f.fact(key):
            missing.append(label)
    return _finish("gst_notice", checks, [], missing)


def verify_tender(facts: List[Fact], currency: str, ocr: bool) -> VerificationReport:
    f = _Facts(facts)
    checks: List[VerificationCheck] = []
    pac, emd, fee = f.amount("estimate_value"), f.amount("emd"), f.amount("tender_fee")
    if pac is not None and emd is not None and pac > 0:
        share = (emd / pac * 100).quantize(Decimal("0.01"))
        checks.append(
            VerificationCheck(
                key="emd_share",
                label="EMD as a share of the estimate",
                status="verified" if share <= Decimal("5") else "needs_attention",
                formula="EMD ÷ PAC × 100",
                inputs=[_input("EMD", emd, currency), _input("Estimate (PAC)", pac, currency)],
                calculated_value="%s%%" % share,
                explanation=(
                    "EMD is %s%% of the estimated contract value. Public works tenders commonly "
                    "set it at 1–2.5%%; check the tender's own rule if it looks high." % share
                ),
                page=f.fact("emd").page,
                source_text=f.fact("emd").source_text,
            )
        )
    if emd is not None or fee is not None:
        outlay = (emd or Decimal(0)) + (fee or Decimal(0))
        parts = [label for label, v in (("EMD", emd), ("Tender fee", fee)) if v is not None]
        checks.append(
            VerificationCheck(
                key="upfront",
                label="Cash needed to bid",
                status="verified",
                formula=" + ".join(parts),
                inputs=[_input(l, v, currency) for l, v in (("EMD", emd), ("Tender fee", fee)) if v is not None],
                calculated_value=money.fmt(outlay, currency),
                explanation="Amount to arrange before submitting. EMD is normally refunded to unsuccessful bidders; the tender fee is not.",
            )
        )
    missing = [label for key, label in (("emd", "EMD / bid security"), ("submission_deadline", "Submission deadline")) if not f.fact(key)]
    return _finish("tender", checks, [], missing)


def verify_rental(facts: List[Fact], currency: str, ocr: bool) -> VerificationReport:
    f = _Facts(facts)
    checks: List[VerificationCheck] = []
    rent, deposit = f.amount("rent"), f.amount("deposit")
    if rent and deposit:
        months = (deposit / rent).quantize(Decimal("0.1"))
        checks.append(
            VerificationCheck(
                key="deposit_months",
                label="Deposit in months of rent",
                status="verified" if months <= 6 else "needs_attention",
                formula="Deposit ÷ monthly rent",
                inputs=[_input("Security deposit", deposit, currency, page=f.fact("deposit").page),
                        _input("Monthly rent", rent, currency, page=f.fact("rent").page)],
                calculated_value="%s months" % _num(months),
                explanation=(
                    "The deposit equals %s months of rent." % _num(months)
                    + (" That is on the high side; confirm the refund terms in writing." if months > 6 else "")
                ),
            )
        )
        duration = _months(f.fact("duration").value) if f.fact("duration") else None
        if duration:
            total = money.q(rent * duration)
            checks.append(
                VerificationCheck(
                    key="total_rent",
                    label="Rent over the full term",
                    status="verified",
                    formula="%s × %d months" % (money.fmt(rent, currency), duration),
                    inputs=[_input("Monthly rent", rent, currency),
                            {"label": "Months", "value": str(duration), "source": "extracted"}],
                    calculated_value=money.fmt(total, currency),
                    explanation="Total rent payable over the agreement, before any escalation or maintenance charges.",
                    assumptions=["Assumes no rent increase during the term."],
                )
            )
    missing = [label for key, label in (("rent", "Monthly rent"), ("deposit", "Security deposit")) if not f.fact(key)]
    return _finish("rental", checks, [], missing)


def verify_insurance(facts: List[Fact], currency: str, ocr: bool) -> VerificationReport:
    f = _Facts(facts)
    checks: List[VerificationCheck] = []
    cover, premium = f.amount("sum_insured"), f.amount("premium")
    copay_fact = f.fact("copayment")
    if cover and premium:
        share = (premium / cover * 100).quantize(Decimal("0.01"))
        checks.append(
            VerificationCheck(
                key="premium_share",
                label="Premium per Rs. 100 of cover",
                status="verified",
                formula="Premium ÷ sum insured × 100",
                inputs=[_input("Premium", premium, currency), _input("Sum insured", cover, currency)],
                calculated_value="%s%%" % share,
                explanation="You pay %s for every Rs. 100 of cover. Use this to compare quotes." % money.fmt(premium / cover * 100, currency),
            )
        )
    if copay_fact and cover:
        pct = money.parse_percent(copay_fact.value)
        if pct is not None:
            example = Decimal(100000) if cover >= 100000 else cover
            share = money.pct_of(example, pct)
            checks.append(
                VerificationCheck(
                    key="copay_example",
                    label="Co-payment on a %s claim" % money.fmt(example, currency),
                    status="verified",
                    formula="%s × %s%%" % (money.fmt(example, currency), _num(pct)),
                    inputs=[_input("Example claim", example, currency, source="calculated"),
                            _input("Co-payment", pct, currency, percent=True, page=copay_fact.page)],
                    calculated_value=money.fmt(share, currency),
                    explanation="On an admissible claim of this size you would pay %s yourself." % money.fmt(share, currency),
                    assumptions=["Illustrative claim amount chosen by Doc Decode, not taken from the policy."],
                    page=copay_fact.page,
                    source_text=copay_fact.source_text,
                )
            )
    missing = [label for key, label in (("sum_insured", "Sum insured"), ("premium", "Premium")) if not f.fact(key)]
    return _finish("insurance", checks, [], missing)


# ---------------------------------------------------------------------------

def _finish(kind: str, checks: List[VerificationCheck], assumptions: List[str],
            missing: List[str]) -> VerificationReport:
    statuses = [c.status for c in checks]
    if "mismatch" in statuses:
        status = "mismatch"
    elif "needs_attention" in statuses:
        status = "needs_attention"
    elif statuses and all(s == "verified" for s in statuses):
        status = "verified" if not missing else "missing_information"
    elif missing:
        status = "missing_information"
    else:
        status = "unable_to_verify"

    mismatches = sum(1 for s in statuses if s == "mismatch")
    attention = sum(1 for s in statuses if s == "needs_attention")
    passed = sum(1 for s in statuses if s == "verified")
    if status == "mismatch":
        headline = "%d calculation%s on this document do%s not add up." % (
            mismatches, "s" if mismatches != 1 else "", "es" if mismatches == 1 else "")
    elif status == "needs_attention":
        headline = "%d figure%s need%s checking against the original." % (
            attention, "s" if attention != 1 else "", "s" if attention == 1 else "")
    elif status == "verified":
        headline = "All %d calculation%s check out." % (passed, "s" if passed != 1 else "")
    elif status == "missing_information":
        headline = (
            "%d check%s passed, but some figures needed for a full check are missing."
            % (passed, "s" if passed != 1 else "") if passed
            else "Some figures needed to verify this document are missing."
        )
    else:
        headline = "Doc Decode could not find figures on this document that it can check."

    return VerificationReport(
        applicable=bool(checks) or bool(missing),
        kind=kind,
        kind_label=KIND_LABELS.get(kind, "Calculations"),
        status=status,
        headline=headline,
        checks=checks,
        assumptions=assumptions,
        missing_fields=missing,
    )


def verify(doc_type: str, facts: List[Fact], items: List[LineItem], currency: str = "Rs.",
           ocr: bool = False) -> VerificationReport:
    if doc_type in ("invoice", "hospital_bill", "purchase_order"):
        kind = {"hospital_bill": "hospital_bill", "purchase_order": "purchase_order"}.get(doc_type, "invoice")
        return verify_invoice(facts, items, currency, ocr, kind=kind)
    if doc_type == "loan_agreement":
        return verify_loan(facts, currency, ocr)
    if doc_type in ("gst_notice", "government_notice"):
        return verify_demand(facts, currency, ocr)
    if doc_type == "tender":
        return verify_tender(facts, currency, ocr)
    if doc_type == "rental_agreement":
        return verify_rental(facts, currency, ocr)
    if doc_type == "insurance":
        return verify_insurance(facts, currency, ocr)
    # Any other document that still carries an invoice-shaped table gets the
    # same arithmetic; otherwise there is nothing honest to verify.
    if items:
        return verify_invoice(facts, items, currency, ocr, kind="invoice")
    return VerificationReport(applicable=False, kind="none", status="unable_to_verify",
                              headline="This document type has no calculations to verify.")
