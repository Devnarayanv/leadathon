"""Arithmetic checks on the figures a document states.

Every check re-does one piece of arithmetic with Decimal (see money.py) and
reports the formula, the inputs, what the document says and what the
arithmetic gives. A check the document cannot support is reported as
missing_information with the reason. It is never run on a zero and never
reported as passed.

Only figures the document states are used. The one derived value is a
calculation the document's own numbers imply (for example tax = base x rate).
"""
import datetime as dt
from decimal import Decimal, localcontext
from typing import Dict, List, Optional, Sequence, Tuple

import money
from document_classifier import label_for
from schemas import Fact, LineItem, VerificationCheck, VerificationReport

TOLERANCE = Decimal("1.00")
MAX_LINE_CHECKS = 40

_DATE_FORMATS = (
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%Y-%m-%d",
    "%d %B %Y", "%d %b %Y", "%d %B, %Y", "%d %b, %Y",
)


class _Figures:
    """Read-only view of the document's stated facts."""

    def __init__(self, facts: Sequence[Fact]):
        self.by_key: Dict[str, Fact] = {fact.key: fact for fact in facts}

    def fact(self, key: str) -> Optional[Fact]:
        return self.by_key.get(key)

    def money(self, key: str) -> Optional[Decimal]:
        fact = self.fact(key)
        return money.parse(fact.value) if fact else None

    def pct(self, key: str) -> Optional[Decimal]:
        fact = self.fact(key)
        return money.parse_percent(fact.value) if fact else None

    def text(self, key: str) -> Optional[str]:
        fact = self.fact(key)
        return fact.value if fact else None

    def where(self, key: str) -> Tuple[Optional[int], Optional[str]]:
        fact = self.fact(key)
        return (fact.page, fact.source_text) if fact else (None, None)


def _check(
    key: str,
    label: str,
    status: str,
    *,
    formula: str = "",
    inputs: Sequence[Tuple[str, str]] = (),
    stated: Optional[Decimal] = None,
    calculated: Optional[Decimal] = None,
    explanation: str = "",
    page: Optional[int] = None,
    source: Optional[str] = None,
    assumptions: Sequence[str] = (),
) -> VerificationCheck:
    difference = None
    if stated is not None and calculated is not None:
        difference = money.fmt(money.q(stated - calculated))
    return VerificationCheck(
        key=key,
        label=label,
        status=status,
        formula=formula,
        inputs=[{"name": name, "value": value} for name, value in inputs],
        document_value=money.fmt(stated) if stated is not None else None,
        calculated_value=money.fmt(calculated) if calculated is not None else None,
        difference=difference,
        explanation=explanation,
        page=page,
        source_text=source,
        assumptions=list(assumptions),
    )


def _compare_status(stated: Decimal, calculated: Decimal) -> str:
    return "verified" if money.within_tolerance(stated, calculated, TOLERANCE) else "mismatch"


def _dec(text: Optional[str]) -> Optional[Decimal]:
    return money.parse(text) if text else None


def _compared(
    key: str,
    label: str,
    stated: Optional[Decimal],
    calculated: Decimal,
    formula: str,
    inputs: Sequence[Tuple[str, str]],
    page: Optional[int],
    source: Optional[str],
    assumptions: Sequence[str] = (),
) -> VerificationCheck:
    """A check where both sides are known, or the document's side is missing."""
    if stated is None:
        return _check(
            key, label, "missing_information", formula=formula, inputs=inputs,
            calculated=calculated, page=page, source=source,
            explanation="The document does not state this figure. The calculated value is shown for reference only.",
            assumptions=assumptions,
        )
    status = _compare_status(stated, calculated)
    if status == "verified":
        explanation = "The stated figure agrees with the calculation."
    else:
        explanation = "The calculation gives %s, but the document states %s." % (
            money.fmt(calculated), money.fmt(stated),
        )
    return _check(
        key, label, status, formula=formula, inputs=inputs, stated=stated,
        calculated=calculated, explanation=explanation, page=page, source=source,
        assumptions=assumptions,
    )


def _invoice_checks(figures: _Figures, items: Sequence[LineItem]) -> Tuple[List[VerificationCheck], List[str]]:
    checks: List[VerificationCheck] = []
    assumptions: List[str] = []

    subtotal = figures.money("subtotal")
    discount = figures.money("discount")
    taxable = figures.money("taxable_value")
    total = figures.money("total")
    sub_page, sub_src = figures.where("subtotal")

    # 1. Each row: quantity x rate = amount.
    if not items:
        checks.append(_check(
            "line_items", "Line items", "missing_information",
            explanation="No quantity, rate and amount rows could be read from the table, so row arithmetic was not run.",
        ))
    for number, item in enumerate(items[:MAX_LINE_CHECKS], start=1):
        label = "Line %d: %s" % (number, item.description[:60])
        qty, rate, amount = _dec(item.quantity), _dec(item.unit_price), _dec(item.amount)
        if qty is None or rate is None or amount is None:
            checks.append(_check(
                "line_%d" % number, label, "missing_information",
                formula="quantity x rate = amount",
                explanation="Quantity, rate or amount is not stated on this row.",
                page=item.page, source=item.source_text,
            ))
            continue
        calculated = money.q(qty * rate)
        checks.append(_compared(
            "line_%d" % number, label, amount, calculated,
            formula="quantity x rate = amount",
            inputs=[("quantity", item.quantity or ""), ("rate", item.unit_price or "")],
            page=item.page, source=item.source_text,
        ))

    # 2. Sum of rows against the stated subtotal.
    amounts = [_dec(item.amount) for item in items]
    if items and all(value is not None for value in amounts):
        lines_sum = money.q(sum(amounts, Decimal(0)))
        checks.append(_compared(
            "lines_sum", "Sum of rows against subtotal", subtotal, lines_sum,
            formula="sum of row amounts = subtotal",
            inputs=[("sum of row amounts", money.fmt(lines_sum))],
            page=sub_page, source=sub_src,
        ))
    else:
        checks.append(_check(
            "lines_sum", "Sum of rows against subtotal", "missing_information",
            formula="sum of row amounts = subtotal",
            explanation="Row amounts are incomplete, so their sum cannot be taken.",
            page=sub_page, source=sub_src,
        ))

    # 3. Discount and taxable value.
    base: Optional[Decimal] = None
    if discount is not None:
        if subtotal is None:
            checks.append(_check(
                "taxable_after_discount", "Taxable value after discount", "missing_information",
                formula="subtotal - discount = taxable value",
                explanation="A discount is stated but the subtotal is not.",
            ))
        else:
            expected = money.q(subtotal - discount)
            if taxable is not None:
                checks.append(_compared(
                    "taxable_after_discount", "Taxable value after discount", taxable, expected,
                    formula="subtotal - discount = taxable value",
                    inputs=[("subtotal", money.fmt(subtotal)), ("discount", money.fmt(discount))],
                    page=figures.where("taxable_value")[0], source=figures.where("taxable_value")[1],
                ))
            else:
                checks.append(_check(
                    "taxable_after_discount", "Taxable value after discount", "missing_information",
                    formula="subtotal - discount = taxable value", calculated=expected,
                    explanation="A discount is stated but the taxable value is not, so the result cannot be matched to the document.",
                ))
            base = taxable if taxable is not None else expected
    else:
        if taxable is not None and subtotal is not None:
            checks.append(_compared(
                "taxable_value", "Taxable value against subtotal", taxable, subtotal,
                formula="taxable value = subtotal (no discount stated)",
                inputs=[("subtotal", money.fmt(subtotal))],
                page=figures.where("taxable_value")[0], source=figures.where("taxable_value")[1],
            ))
            base = taxable
        elif taxable is not None:
            base = taxable
        elif subtotal is not None:
            base = subtotal
            assumptions.append("No taxable value is stated, so the subtotal is used as the taxable base.")
    if discount is None:
        assumptions.append("No discount is stated, so none is subtracted.")

    # 4. Each tax line: taxable base x stated rate = stated amount.
    tax_amounts: List[Decimal] = []
    tax_complete = True
    any_tax = False
    for key, name in (("cgst", "CGST"), ("sgst", "SGST"), ("igst", "IGST")):
        amount = figures.money(key)
        rate = figures.pct(key + "_rate")
        if amount is None and rate is None:
            continue
        any_tax = True
        page, source = figures.where(key)
        if amount is None:
            tax_complete = False
            checks.append(_check(
                "tax_%s" % key, "%s amount" % name, "missing_information",
                formula="taxable value x rate = %s" % name,
                explanation="The %s rate is stated but the amount is not." % name,
                page=page, source=source,
            ))
            continue
        tax_amounts.append(amount)
        if base is None:
            checks.append(_check(
                "tax_%s" % key, "%s against taxable value" % name, "missing_information",
                formula="taxable value x rate = %s" % name, stated=amount,
                explanation="No taxable value is available, so the %s cannot be recomputed." % name,
                page=page, source=source,
            ))
        elif rate is None:
            checks.append(_check(
                "tax_%s" % key, "%s against taxable value" % name, "missing_information",
                formula="taxable value x rate = %s" % name, stated=amount,
                explanation="The %s rate is not stated, so the amount cannot be recomputed." % name,
                page=page, source=source,
            ))
        else:
            calculated = money.pct_of(base, rate)
            checks.append(_compared(
                "tax_%s" % key, "%s against taxable value" % name, amount, calculated,
                formula="taxable value x %s%% = %s" % (rate.normalize(), name),
                inputs=[("taxable value", money.fmt(base)), ("rate", "%s%%" % rate.normalize())],
                page=page, source=source,
            ))
    if not any_tax:
        checks.append(_check(
            "tax_lines", "Tax (CGST, SGST or IGST)", "missing_information",
            explanation="No CGST, SGST or IGST amount is stated.",
        ))

    # 5. Subtotal + tax - discount = total.
    tax_total = money.q(sum(tax_amounts, Decimal(0))) if tax_amounts and tax_complete else None
    total_page, total_src = figures.where("total")
    if total is None or subtotal is None or tax_total is None:
        missing = [name for name, value in (("total", total), ("subtotal", subtotal), ("tax amounts", tax_total)) if value is None]
        checks.append(_check(
            "total", "Total against subtotal, tax and discount", "missing_information",
            formula="subtotal + tax - discount = total",
            explanation="Needed but not stated: %s." % ", ".join(missing),
            page=total_page, source=total_src,
        ))
    else:
        discount_used = discount or Decimal(0)
        expected = money.q(subtotal + tax_total - discount_used)
        checks.append(_compared(
            "total", "Total against subtotal, tax and discount", total, expected,
            formula="subtotal + tax - discount = total",
            inputs=[
                ("subtotal", money.fmt(subtotal)),
                ("tax", money.fmt(tax_total)),
                ("discount", money.fmt(discount_used)),
            ],
            page=total_page, source=total_src,
        ))
    return checks, assumptions


def _tender_checks(figures: _Figures) -> Tuple[List[VerificationCheck], List[str]]:
    estimated = figures.money("estimated_value")
    percent = figures.pct("emd_percent")
    emd = figures.money("emd")
    page, source = figures.where("emd")
    if estimated is None or percent is None:
        return [_check(
            "emd", "EMD against estimated value", "missing_information",
            formula="estimated value x EMD% = EMD", stated=emd,
            explanation="The estimated value or the EMD percentage is not stated, so the deposit cannot be recomputed.",
            page=page, source=source,
        )], []
    calculated = money.pct_of(estimated, percent)
    return [_compared(
        "emd", "EMD against estimated value", emd, calculated,
        formula="estimated value x %s%% = EMD" % percent.normalize(),
        inputs=[("estimated value", money.fmt(estimated)), ("EMD rate", "%s%%" % percent.normalize())],
        page=page, source=source,
    )], []


def _months(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    digits = "".join(ch for ch in text.split(" ")[0] if ch.isdigit())
    return int(digits) if digits else None


def emi(principal: Decimal, annual_percent: Decimal, months: int) -> Decimal:
    """Standard reducing-balance EMI, computed in Decimal at 28 digits."""
    with localcontext() as context:
        context.prec = 28
        rate = annual_percent / Decimal(100) / Decimal(12)
        if rate == 0:
            return money.q(principal / Decimal(months))
        growth = (Decimal(1) + rate) ** months
        return money.q(principal * rate * growth / (growth - Decimal(1)))


def _loan_checks(figures: _Figures) -> Tuple[List[VerificationCheck], List[str]]:
    principal = figures.money("principal")
    rate = figures.pct("annual_rate")
    months = _months(figures.text("tenure_months"))
    stated = figures.money("emi")
    page, source = figures.where("emi")
    absent = [
        name for name, value in (
            ("loan amount (principal)", principal),
            ("annual interest rate", rate),
            ("tenure in months", months),
        ) if value is None or value == 0
    ]
    if absent:
        return [_check(
            "emi", "EMI against principal, rate and tenure", "missing_information",
            formula="EMI = P x r x (1+r)^n / ((1+r)^n - 1)",
            explanation="EMI is checked only when principal, annual rate and tenure are all stated. Not stated: %s." % ", ".join(absent),
            page=page, source=source,
        )], []
    calculated = emi(principal, rate, months)
    return [_compared(
        "emi", "EMI against principal, rate and tenure", stated, calculated,
        formula="EMI = P x r x (1+r)^n / ((1+r)^n - 1), r = annual rate / 12",
        inputs=[
            ("principal P", money.fmt(principal)),
            ("annual rate", "%s%%" % rate.normalize()),
            ("tenure n", "%d months" % months),
        ],
        page=page, source=source,
    )], []


def _parse_date(text: Optional[str]) -> Optional[dt.date]:
    if not text:
        return None
    cleaned = text.strip().replace(",", ", ").replace(",  ", ", ")
    for pattern in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue
    return None


def _insurance_checks(figures: _Figures) -> Tuple[List[VerificationCheck], List[str]]:
    start_text = figures.text("policy_start")
    end_text = figures.text("policy_end")
    start, end = _parse_date(start_text), _parse_date(end_text)
    page, source = figures.where("policy_end")
    if start is None or end is None:
        return [_check(
            "policy_period", "Policy period", "missing_information",
            formula="policy end date is after policy start date",
            explanation="The policy start or end date is not stated in a form that can be read.",
            page=page, source=source,
        )], []
    days = (end - start).days
    status = "verified" if days > 0 else "mismatch"
    explanation = (
        "The policy runs from %s to %s (%d days)." % (start.isoformat(), end.isoformat(), days)
        if status == "verified"
        else "The policy end date (%s) is not after the start date (%s)." % (end.isoformat(), start.isoformat())
    )
    return [_check(
        "policy_period", "Policy period", status,
        formula="policy end date is after policy start date",
        inputs=[("start", start.isoformat()), ("end", end.isoformat())],
        explanation=explanation, page=page, source=source,
    )], []


def _rent_checks(figures: _Figures) -> Tuple[List[VerificationCheck], List[str]]:
    rent = figures.money("monthly_rent")
    escalation = figures.pct("rent_escalation")
    page, source = figures.where("rent_escalation")
    if rent is None or escalation is None:
        return [_check(
            "rent_escalation", "Rent after escalation", "missing_information",
            formula="rent x (1 + escalation%) = revised rent",
            explanation="Both the monthly rent and the escalation percentage must be stated to check the escalation.",
            page=page, source=source,
        )], []
    calculated = money.q(rent * (1 + escalation / Decimal(100)))
    return [_check(
        "rent_escalation", "Rent after escalation", "missing_information",
        formula="rent x (1 + escalation%) = revised rent",
        inputs=[("monthly rent", money.fmt(rent)), ("escalation", "%s%%" % escalation.normalize())],
        calculated=calculated, page=page, source=source,
        explanation="The agreement states an escalation but not the revised rent, so there is no stated figure to compare against. The calculated figure is shown for reference.",
    )], []


_KIND_FOR_TYPE = {
    "invoice": "Invoice arithmetic",
    "purchase_order": "Purchase order arithmetic",
    "tender": "Tender deposit",
    "loan_agreement": "Loan EMI",
    "insurance": "Policy period",
    "rental_agreement": "Rent escalation",
}


def verify(doc_type: str, facts: Sequence[Fact], items: Sequence[LineItem]) -> VerificationReport:
    """The document-level verification report for one document."""
    figures = _Figures(facts)
    if doc_type in ("invoice", "purchase_order"):
        checks, assumptions = _invoice_checks(figures, items)
    elif doc_type == "tender":
        checks, assumptions = _tender_checks(figures)
    elif doc_type == "loan_agreement":
        checks, assumptions = _loan_checks(figures)
    elif doc_type == "insurance":
        checks, assumptions = _insurance_checks(figures)
    elif doc_type == "rental_agreement":
        checks, assumptions = _rent_checks(figures)
    else:
        return VerificationReport(
            applicable=False,
            kind="none",
            kind_label=label_for(doc_type),
            status="unable_to_verify",
            headline="No arithmetic checks apply to this document type. Figures are shown as the document states them.",
        )

    statuses = [check.status for check in checks]
    if "mismatch" in statuses:
        status = "mismatch"
    elif "missing_information" in statuses:
        status = "missing_information"
    elif checks and all(s == "verified" for s in statuses):
        status = "verified"
    elif "needs_attention" in statuses:
        status = "needs_attention"
    else:
        status = "unable_to_verify"

    total = len(checks)
    agree = statuses.count("verified")
    disagree = statuses.count("mismatch")
    missing = statuses.count("missing_information")
    if not checks:
        headline = "No figures were found to check, so no arithmetic was run."
    elif status == "mismatch":
        headline = "%d of %d checks do not agree with the document's own figures." % (disagree, total)
    elif status == "verified":
        headline = "All %d checks agree with the document's own figures." % total
    elif status == "missing_information":
        headline = "%d of %d checks agree. %d could not run because the document does not state what they need." % (
            agree, total, missing,
        )
    else:
        headline = "%d of %d checks agree." % (agree, total)

    missing_fields = [check.label for check in checks if check.status == "missing_information"]
    return VerificationReport(
        applicable=True,
        kind=doc_type,
        kind_label=_KIND_FOR_TYPE.get(doc_type, label_for(doc_type)),
        status=status,
        headline=headline,
        checks=checks,
        assumptions=assumptions,
        missing_fields=missing_fields,
    )
