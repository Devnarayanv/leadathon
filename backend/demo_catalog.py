"""The allowlist of demo documents the app may serve.

The browser asks for a demo by id, never by path. Only the ids below resolve,
and each maps to a fixed filename in demo/. Every demo is fictional and labelled
SYNTHETIC in its own text.
"""
from pathlib import Path
from typing import List, Optional

from schemas import DemoDocument

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo"

_ENTRIES = [
    {
        "id": "sample_invoice_mismatch",
        "label": "Invoice with one wrong line",
        "description": "Synthetic tax invoice. One row's amount does not equal quantity x rate.",
        "doc_type": "invoice",
        "filename": "sample_invoice_mismatch.pdf",
        "highlight": "Cable clips: 20 x 15.00 is 300.00, but the row states 350.00.",
    },
    {
        "id": "sample_purchase_order",
        "label": "Matching purchase order",
        "description": "Synthetic purchase order for the same supplier and buyer as the invoice.",
        "doc_type": "purchase_order",
        "filename": "sample_purchase_order.pdf",
        "highlight": "Compare with the invoice to see the cable clips amount differ.",
    },
    {
        "id": "sample_tender",
        "label": "Tender notice",
        "description": "Synthetic tender with EMD, turnover, certification and a document list.",
        "doc_type": "tender",
        "filename": "sample_tender.pdf",
        "highlight": "EMD is 2% of the estimated value; eligibility and documents are listed.",
    },
    {
        "id": "sample_gst_notice",
        "label": "GST notice",
        "description": "Synthetic GST notice with a demand, interest, penalty and reply date.",
        "doc_type": "gst_notice",
        "filename": "sample_gst_notice.pdf",
        "highlight": "A reply date and a demanded amount are stated.",
    },
    {
        "id": "sample_insurance_policy",
        "label": "Insurance policy schedule",
        "description": "Synthetic policy schedule with sum insured, premium and policy period.",
        "doc_type": "insurance",
        "filename": "sample_insurance_policy.pdf",
        "highlight": "Policy period and premium are stated.",
    },
    {
        "id": "sample_loan",
        "label": "Loan sanction with stated EMI",
        "description": "Synthetic loan letter with principal, rate, tenure and a stated EMI.",
        "doc_type": "loan_agreement",
        "filename": "sample_loan.pdf",
        "highlight": "The stated EMI is checked against principal, rate and tenure.",
    },
    {
        "id": "sample_ambiguous_dates",
        "label": "Notice with ambiguous dates",
        "description": "Synthetic notice whose dates are written two ways and tied to relative periods.",
        "doc_type": "government_notice",
        "filename": "sample_ambiguous_dates.pdf",
        "highlight": "Dates that cannot be resolved to one day are flagged for checking.",
    },
    {
        "id": "sample_no_deadlines",
        "label": "Letter with no deadlines",
        "description": "Synthetic plain letter with no dates or payment obligations.",
        "doc_type": "other",
        "filename": "sample_no_deadlines.pdf",
        "highlight": "Nothing in this letter should produce a deadline.",
    },
    {
        "id": "demo_rental_agreement",
        "label": "Rental agreement",
        "description": "Synthetic residential rental agreement.",
        "doc_type": "rental_agreement",
        "filename": "demo_rental_agreement.pdf",
        "highlight": "Recurring rent date and notice windows.",
    },
    {
        "id": "demo_loan_agreement",
        "label": "Personal loan agreement",
        "description": "Synthetic personal loan agreement.",
        "doc_type": "loan_agreement",
        "filename": "demo_loan_agreement.pdf",
        "highlight": "Loan terms and repayment clauses.",
    },
    {
        "id": "demo_hospital_bill",
        "label": "Hospital bill",
        "description": "Synthetic hospital bill.",
        "doc_type": "hospital_bill",
        "filename": "demo_hospital_bill.pdf",
        "highlight": "Charges and payment dates.",
    },
    {
        "id": "demo_government_notice",
        "label": "Government notice",
        "description": "Synthetic government notice.",
        "doc_type": "government_notice",
        "filename": "demo_government_notice.pdf",
        "highlight": "Response deadlines.",
    },
]

_BY_ID = {entry["id"]: entry for entry in _ENTRIES}


def _entry_path(entry: dict) -> Path:
    return DEMO_DIR / entry["filename"]


def list_documents() -> List[DemoDocument]:
    """Allowlisted demos whose file is actually present in demo/."""
    out: List[DemoDocument] = []
    for entry in _ENTRIES:
        path = _entry_path(entry)
        if not path.is_file():
            continue
        out.append(
            DemoDocument(
                id=entry["id"],
                label=entry["label"],
                description=entry["description"],
                doc_type=entry["doc_type"],
                filename=entry["filename"],
                size_bytes=path.stat().st_size,
                highlight=entry["highlight"],
            )
        )
    return out


def file_bytes(demo_id: str) -> Optional[bytes]:
    """The PDF for an allowlisted id, or None for an unknown or missing demo."""
    entry = _BY_ID.get(demo_id)
    if entry is None:
        return None
    path = _entry_path(entry)
    if not path.is_file():
        return None
    return path.read_bytes()


def filename_for(demo_id: str) -> Optional[str]:
    entry = _BY_ID.get(demo_id)
    return entry["filename"] if entry else None
