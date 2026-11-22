"""Keyword/rule document classification. No LLM call needed.

Classification reads the extracted text, never the file name: a file called
"invoice.pdf" that holds a rental agreement is classified as a rental
agreement. Where the winning score is close to the runner-up, the result is
reported as uncertain and the workspace asks the user to confirm.
"""
from typing import Dict, List, Optional, Tuple

from schemas import Classification, DocTypeOption
from utils import normalise, normalise_phrase

# (phrase, weight). Weights reflect how strongly a phrase pins the type down.
RULES: Dict[str, Dict] = {
    "invoice": {
        "label": "Invoice",
        "terms": [
            ("tax invoice", 7),
            ("invoice no", 5),
            ("invoice number", 5),
            ("invoice date", 4),
            ("bill of supply", 6),
            ("proforma invoice", 6),
            ("hsn", 4),
            ("sac code", 4),
            ("taxable value", 4),
            ("cgst", 4),
            ("sgst", 4),
            ("igst", 4),
            ("place of supply", 4),
            ("gstin", 3),
            ("amount in words", 2),
            ("unit price", 2),
            ("qty", 2),
            ("subtotal", 2),
            ("grand total", 2),
            ("e. & o.e", 2),
            ("reverse charge", 3),
            # Malayalam
            ("ഇൻവോയ്സ്", 5),
            ("നികുതി ബിൽ", 5),
        ],
    },
    "purchase_order": {
        "label": "Purchase order",
        "terms": [
            ("purchase order", 8),
            ("po no", 5),
            ("po number", 5),
            ("order no", 3),
            ("supplier", 3),
            ("vendor code", 4),
            ("delivery schedule", 4),
            ("ship to", 3),
            ("bill to", 2),
            ("ordered quantity", 5),
            ("terms of delivery", 4),
            ("please supply", 5),
            ("this purchase order", 6),
        ],
    },
    "tender": {
        "label": "Tender notice",
        "terms": [
            ("tender notice", 8),
            ("e-tender", 7),
            ("etender", 7),
            ("notice inviting tender", 8),
            ("nit no", 5),
            ("tender reference", 5),
            ("bid security", 6),
            ("earnest money", 6),
            ("emd", 5),
            ("tender fee", 5),
            ("tender document", 4),
            ("bid submission", 6),
            ("bid opening", 6),
            ("technical bid", 5),
            ("financial bid", 5),
            ("performance security", 5),
            ("pre-bid", 4),
            ("prequalification", 4),
            ("pre-qualification", 4),
            ("tender inviting authority", 6),
            ("bidder", 4),
            ("eligibility criteria", 4),
            ("estimate pac", 4),
            # Malayalam
            ("ടെൻഡർ", 6),
            ("ലേലം", 3),
        ],
    },
    "gst_notice": {
        "label": "GST notice",
        "terms": [
            ("gst notice", 8),
            ("goods and services tax", 6),
            ("gstr-1", 6),
            ("gstr-3b", 6),
            ("gstr 3b", 6),
            ("form gst", 6),
            ("drc-01", 7),
            ("drc-07", 7),
            ("asmt-10", 7),
            ("reg-17", 6),
            ("section 73", 6),
            ("section 74", 6),
            ("input tax credit", 5),
            ("itc", 3),
            ("tax period", 4),
            ("state tax officer", 5),
            ("central tax", 4),
            ("gstin", 4),
            ("scrutiny of returns", 6),
            ("show cause notice", 4),
            ("interest and penalty", 4),
        ],
    },
    "rental_agreement": {
        "label": "Rental agreement",
        "terms": [
            ("rental agreement", 6),
            ("lease agreement", 6),
            ("rent agreement", 6),
            ("leave and licence", 6),
            ("leave and license", 6),
            ("tenancy", 4),
            ("lessor", 4),
            ("lessee", 4),
            ("landlord", 4),
            ("tenant", 4),
            ("security deposit", 3),
            ("monthly rent", 3),
            ("licence fee", 2),
            ("premises", 2),
            ("vacate", 2),
            ("lock-in period", 2),
            # Malayalam
            ("വാടക", 5),          # rent
            ("വാടകക്കാരൻ", 4),     # tenant
            ("കരാർ", 3),          # agreement
            ("ഡിപ്പോസിറ്റ്", 3),    # deposit
            ("വീട്", 2),           # house
            ("ഒഴിയ", 2),          # vacate
        ],
    },
    "loan_agreement": {
        "label": "Loan document",
        "terms": [
            ("loan agreement", 6),
            ("sanction letter", 5),
            ("credit facility", 5),
            ("borrower", 4),
            ("lender", 4),
            ("principal amount", 3),
            ("loan amount", 3),
            ("rate of interest", 3),
            ("interest rate", 3),
            ("emi", 3),
            ("equated monthly", 4),
            ("repayment", 3),
            ("processing fee", 2),
            ("tenure", 2),
            ("foreclosure", 3),
            ("prepayment", 2),
            ("collateral", 2),
            ("moratorium", 3),
            ("amortisation", 3),
            # Malayalam
            ("വായ്പ", 5),          # loan
            ("പലിശ", 4),          # interest
            ("തിരിച്ചടവ്", 4),      # repayment
            ("ഗഡു", 3),           # instalment
            ("ബാങ്ക്", 2),          # bank
        ],
    },
    "contract": {
        "label": "Contract / service agreement",
        "terms": [
            ("service agreement", 7),
            ("this agreement is made", 6),
            ("master services agreement", 8),
            ("work order", 4),
            ("scope of work", 5),
            ("statement of work", 6),
            ("annual maintenance contract", 7),
            ("amc", 3),
            ("service level", 4),
            ("deliverables", 4),
            ("indemnify", 4),
            ("force majeure", 4),
            ("governing law", 3),
            ("arbitration", 3),
            ("party of the first part", 5),
            ("termination for convenience", 5),
            ("confidentiality", 3),
            ("non-compete", 4),
            ("auto-renewal", 3),
        ],
    },
    "insurance": {
        "label": "Insurance policy",
        "terms": [
            ("insurance policy", 8),
            ("policy schedule", 7),
            ("policy no", 5),
            ("policy number", 5),
            ("sum insured", 7),
            ("premium", 5),
            ("insured", 3),
            ("insurer", 4),
            ("nominee", 3),
            ("waiting period", 6),
            ("pre-existing disease", 7),
            ("co-payment", 6),
            ("copayment", 6),
            ("deductible", 6),
            ("exclusions", 5),
            ("claim intimation", 6),
            ("cashless", 4),
            ("third party administrator", 5),
            ("irdai", 6),
            ("grace period", 4),
            # Malayalam
            ("ഇൻഷുറൻസ്", 6),
            ("പ്രീമിയം", 4),
        ],
    },
    "hospital_bill": {
        "label": "Hospital bill",
        "terms": [
            ("hospital", 4),
            ("discharge summary", 5),
            ("inpatient", 4),
            ("in-patient", 4),
            ("outpatient", 3),
            ("patient name", 4),
            ("bill no", 3),
            ("consultation charges", 4),
            ("room rent", 3),
            ("pharmacy", 3),
            ("laboratory", 2),
            ("investigation charges", 3),
            ("total payable", 2),
            ("ip no", 3),
            ("uhid", 4),
            # Malayalam
            ("ആശുപത്രി", 5),       # hospital
            ("ബിൽ", 4),           # bill
            ("ചികിത്സ", 4),        # treatment
            ("രോഗി", 3),          # patient
            ("മരുന്ന്", 2),         # medicine
        ],
    },
    "financial_statement": {
        "label": "Financial statement",
        "terms": [
            ("balance sheet", 8),
            ("profit and loss", 8),
            ("profit & loss", 8),
            ("statement of accounts", 6),
            ("cash flow statement", 7),
            ("trial balance", 7),
            ("current liabilities", 5),
            ("shareholders funds", 6),
            ("turnover for the year", 6),
            ("as at 31st march", 5),
            ("auditor", 4),
            ("depreciation", 4),
            ("account statement", 5),
            ("opening balance", 4),
            ("closing balance", 4),
        ],
    },
    "business_license": {
        "label": "Business licence / registration",
        "terms": [
            ("certificate of registration", 7),
            ("trade licence", 8),
            ("trade license", 8),
            ("udyam registration", 8),
            ("udyog aadhaar", 7),
            ("shop and establishment", 7),
            ("fssai", 8),
            ("licence no", 4),
            ("license no", 4),
            ("valid until", 3),
            ("valid upto", 3),
            ("renewal of licence", 6),
            ("registration certificate", 6),
            ("incorporation certificate", 7),
            ("cin", 3),
        ],
    },
    "government_notice": {
        "label": "Government notice",
        "terms": [
            ("public notice", 5),
            ("show cause notice", 6),
            ("demand notice", 5),
            ("notice under section", 6),
            ("government of", 4),
            ("municipal corporation", 4),
            ("gram panchayat", 4),
            ("tahsildar", 4),
            ("revenue department", 4),
            ("income tax department", 5),
            ("assessment year", 3),
            ("reference no", 2),
            ("hereby directed", 3),
            ("failing which", 3),
            ("competent authority", 3),
            ("subject:", 1),
            # Malayalam
            ("അറിയിപ്പ്", 4),       # notice
            ("സർക്കാർ", 4),        # government
            ("പഞ്ചായത്ത്", 4),      # panchayat
            ("നഗരസഭ", 4),         # municipality
            ("നികുതി", 3),         # tax
            ("ഉത്തരവ്", 3),        # order
        ],
    },
}

OTHER_LABEL = "Other / uncategorised"

# Below this score the type is reported as uncertain.
CERTAIN_SCORE = 8
# And it must beat the runner-up by this much.
CERTAIN_MARGIN = 3


def label_for(doc_type: str) -> str:
    if doc_type == "other":
        return OTHER_LABEL
    return RULES.get(doc_type, {}).get("label", OTHER_LABEL)


def options() -> List[DocTypeOption]:
    """Every type the user can pick from when correcting a classification."""
    items = [DocTypeOption(key=key, label=rule["label"]) for key, rule in RULES.items()]
    items.sort(key=lambda option: option.label)
    items.append(DocTypeOption(key="other", label=OTHER_LABEL))
    return items


def score_types(text: str) -> List[Tuple[str, int, List[str]]]:
    haystack = normalise(text)
    results: List[Tuple[str, int, List[str]]] = []
    for doc_type, rule in RULES.items():
        score = 0
        matched: List[str] = []
        for phrase, weight in rule["terms"]:
            hits = haystack.count(normalise_phrase(phrase))
            if hits:
                # Repeats add evidence, but with sharply diminishing returns.
                score += weight + min(hits - 1, 3)
                matched.append(phrase)
        if score:
            results.append((doc_type, score, matched))
    results.sort(key=lambda row: row[1], reverse=True)
    return results


def _reason(matched: List[str], score: int) -> str:
    if not matched:
        return "No type-specific wording was found in the extracted text."
    shown = ", ".join('"%s"' % term for term in matched[:4])
    more = " and %d more term(s)" % (len(matched) - 4) if len(matched) > 4 else ""
    return "Matched %s%s in the document text (score %d)." % (shown, more, score)


def classify(text: str) -> Classification:
    if not text.strip():
        return Classification(
            doc_type="other",
            label="Document type uncertain",
            certain=False,
            score=0,
            matched_terms=[],
            reason="No text could be extracted, so there was nothing to classify.",
        )

    ranked = score_types(text)
    if not ranked:
        return Classification(
            doc_type="other",
            label="Document type uncertain",
            certain=False,
            score=0,
            matched_terms=[],
            reason=_reason([], 0),
        )

    doc_type, score, matched = ranked[0]
    runner_up_key = ranked[1][0] if len(ranked) > 1 else None
    runner_up = ranked[1][1] if len(ranked) > 1 else 0
    certain = score >= CERTAIN_SCORE and (score - runner_up) >= CERTAIN_MARGIN
    label = RULES[doc_type]["label"]
    reason = _reason(matched, score)
    if not certain:
        if runner_up_key and score - runner_up < CERTAIN_MARGIN:
            reason += " %s scored %d, which is too close to call." % (
                RULES[runner_up_key]["label"],
                runner_up,
            )
        else:
            reason += " That is below the confidence threshold of %d." % CERTAIN_SCORE
        return Classification(
            doc_type=doc_type,
            label="Document type uncertain (closest match: %s)" % label.lower(),
            certain=False,
            score=score,
            matched_terms=matched[:8],
            reason=reason,
            runner_up=runner_up_key,
            runner_up_label=RULES[runner_up_key]["label"] if runner_up_key else None,
        )
    return Classification(
        doc_type=doc_type,
        label=label,
        certain=True,
        score=score,
        matched_terms=matched[:8],
        reason=reason,
        runner_up=runner_up_key,
        runner_up_label=RULES[runner_up_key]["label"] if runner_up_key else None,
    )


def forced(doc_type: str, text: str) -> Classification:
    """Classification for a type the user picked by hand."""
    ranked = {key: (score, matched) for key, score, matched in score_types(text)}
    score, matched = ranked.get(doc_type, (0, []))
    return Classification(
        doc_type=doc_type,
        label=label_for(doc_type),
        certain=True,
        score=score,
        matched_terms=matched[:8],
        reason="Document type set by you. The %s analysis pipeline was applied."
        % label_for(doc_type).lower(),
        user_set=True,
    )
