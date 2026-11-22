"""Invoice against purchase order.

Header fields are compared on supplier, buyer, total and tax. Items are paired
by description similarity, then quantity and amount are compared on each pair.
Nothing is compared against a value one side did not state: a missing value is
reported as missing, not as zero.
"""
import difflib
import re
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple

import money
from schemas import (
    ComparableDocument,
    CompareResponse,
    ComparisonRow,
    Fact,
    LineItem,
)

ITEM_MATCH_RATIO = 0.6
NAME_MATCH_RATIO = 0.85


def _fact(facts: Sequence[Fact], key: str) -> Optional[Fact]:
    for fact in facts:
        if fact.key == key:
            return fact
    return None


def _tax_total(facts: Sequence[Fact]) -> Optional[str]:
    amounts = []
    for key in ("cgst", "sgst", "igst"):
        fact = _fact(facts, key)
        parsed = money.parse(fact.value) if fact else None
        if parsed is not None:
            amounts.append(parsed)
    if not amounts:
        return None
    return money.fmt(money.q(sum(amounts, Decimal(0))))


def _value(facts: Sequence[Fact], key: str) -> Optional[str]:
    fact = _fact(facts, key)
    return fact.value if fact else None


def _similar(a: str, b: str) -> float:
    a_clean = " ".join(re.sub(r"[^a-z0-9 ]+", " ", a.lower()).split())
    b_clean = " ".join(re.sub(r"[^a-z0-9 ]+", " ", b.lower()).split())
    return difflib.SequenceMatcher(None, a_clean, b_clean).ratio()


def _text_row(label: str, left: Optional[str], right: Optional[str]) -> Optional[ComparisonRow]:
    if left is None and right is None:
        return None
    if left is None:
        return ComparisonRow(label=label, left_value=None, right_value=right, result="missing_left",
                             note="The invoice does not state this.")
    if right is None:
        return ComparisonRow(label=label, left_value=left, right_value=None, result="missing_right",
                             note="The purchase order does not state this.")
    ratio = _similar(left, right)
    result = "match" if ratio >= NAME_MATCH_RATIO else "mismatch"
    note = "" if result == "match" else "The two documents name this differently (similarity %d%%)." % round(ratio * 100)
    return ComparisonRow(label=label, left_value=left, right_value=right, result=result, note=note)


def _money_row(label: str, left: Optional[str], right: Optional[str]) -> Optional[ComparisonRow]:
    if left is None and right is None:
        return None
    if left is None:
        return ComparisonRow(label=label, left_value=None, right_value=right, result="missing_left",
                             note="The invoice does not state this.")
    if right is None:
        return ComparisonRow(label=label, left_value=left, right_value=None, result="missing_right",
                             note="The purchase order does not state this.")
    a, b = money.parse(left), money.parse(right)
    if a is None or b is None:
        return ComparisonRow(label=label, left_value=left, right_value=right, result="mismatch",
                             note="One value could not be read as an amount.")
    same = money.within_tolerance(a, b)
    note = "" if same else "Difference of %s." % money.fmt(money.q(a - b))
    return ComparisonRow(label=label, left_value=money.fmt(a), right_value=money.fmt(b),
                         result="match" if same else "mismatch", note=note)


def _item_text(item: LineItem) -> str:
    qty = item.quantity or "—"
    amount = money.fmt(money.parse(item.amount)) if item.amount else "—"
    return "qty %s, amount %s" % (qty, amount)


def _item_rows(invoice_items: Sequence[LineItem], po_items: Sequence[LineItem]) -> List[ComparisonRow]:
    rows: List[ComparisonRow] = []
    used = set()
    for item in invoice_items:
        best_index, best_ratio = None, 0.0
        for index, candidate in enumerate(po_items):
            if index in used:
                continue
            ratio = _similar(item.description, candidate.description)
            if ratio > best_ratio:
                best_index, best_ratio = index, ratio
        if best_index is None or best_ratio < ITEM_MATCH_RATIO:
            rows.append(ComparisonRow(
                label=item.description, left_value=_item_text(item), right_value=None,
                result="extra",
                note="On the invoice but not matched to any purchase order line.",
            ))
            continue
        used.add(best_index)
        po_item = po_items[best_index]
        problems = []
        if item.quantity and po_item.quantity and money.parse(item.quantity) != money.parse(po_item.quantity):
            problems.append("quantity %s on the invoice, %s on the order" % (item.quantity, po_item.quantity))
        a, b = money.parse(item.amount or ""), money.parse(po_item.amount or "")
        if a is not None and b is not None and not money.within_tolerance(a, b):
            problems.append("amount %s on the invoice, %s on the order" % (money.fmt(a), money.fmt(b)))
        rows.append(ComparisonRow(
            label=item.description,
            left_value=_item_text(item),
            right_value=_item_text(po_item),
            result="mismatch" if problems else "match",
            note=("; ".join(problems) + ".") if problems else "",
        ))
    for index, po_item in enumerate(po_items):
        if index in used:
            continue
        rows.append(ComparisonRow(
            label=po_item.description, left_value=None, right_value=_item_text(po_item),
            result="missing_right",
            note="On the purchase order but not billed on the invoice.",
        ))
    return rows


def _pair(left: ComparableDocument, right: ComparableDocument) -> Tuple[ComparableDocument, ComparableDocument]:
    return (left, right) if left.doc_type == "invoice" else (right, left)


def compare(left: ComparableDocument, right: ComparableDocument) -> CompareResponse:
    types = {left.doc_type, right.doc_type}

    if types == {"invoice"}:
        left_no = _fact(left.facts, "invoice_number")
        right_no = _fact(right.facts, "invoice_number")
        if left_no and right_no and left_no.value.strip().lower() == right_no.value.strip().lower():
            return CompareResponse(
                comparable=False,
                kind="duplicate_invoice",
                headline="Possible duplicate invoice: both files carry invoice number %s." % left_no.value,
                left_label=left.filename,
                right_label=right.filename,
                notes=[
                    "Check whether the same supply was billed twice before paying either file.",
                    "Two invoices with different numbers are not compared with each other.",
                ],
            )
        return CompareResponse(
            comparable=False,
            kind="none",
            headline="Both files are invoices. Pair one invoice with one purchase order to compare them.",
            left_label=left.filename,
            right_label=right.filename,
        )

    if types != {"invoice", "purchase_order"}:
        return CompareResponse(
            comparable=False,
            kind="none",
            headline="Comparison needs one invoice and one purchase order. This pair has: %s." % ", ".join(
                sorted(t.replace("_", " ") for t in types)
            ),
            left_label=left.filename,
            right_label=right.filename,
            notes=["Choose an invoice and a purchase order to compare them."],
        )

    invoice, order = _pair(left, right)
    field_rows = [
        _text_row("Supplier", _value(invoice.facts, "supplier"), _value(order.facts, "supplier")),
        _text_row("Buyer", _value(invoice.facts, "buyer"), _value(order.facts, "buyer")),
        _money_row("Total", _value(invoice.facts, "total"), _value(order.facts, "total")),
        _money_row("Tax (CGST, SGST, IGST)", _tax_total(invoice.facts), _tax_total(order.facts)),
    ]
    field_rows = [row for row in field_rows if row is not None]
    item_rows = _item_rows(invoice.line_items, order.line_items)

    if not invoice.line_items and not order.line_items:
        notes = ["Neither side has item rows that could be read, so items were not compared."]
    elif not invoice.line_items or not order.line_items:
        notes = ["One side has no readable item rows, so items were not compared item by item."]
    else:
        notes = ["Items are paired by description similarity. Check any unpaired row by hand."]

    problems = [r for r in field_rows + item_rows if r.result in ("mismatch", "extra")]
    compared_count = len([r for r in field_rows + item_rows if r.result in ("match", "mismatch")])
    if not compared_count:
        headline = "Nothing could be compared: the two documents do not state the same fields."
    elif problems:
        headline = "The invoice and purchase order disagree on %d of %d compared points." % (
            len(problems), compared_count,
        )
    else:
        headline = "The invoice agrees with the purchase order on all %d compared points." % compared_count

    return CompareResponse(
        comparable=True,
        kind="invoice_vs_purchase_order",
        headline=headline,
        left_label=invoice.filename,
        right_label=order.filename,
        field_rows=field_rows,
        item_rows=item_rows,
        notes=notes,
    )
