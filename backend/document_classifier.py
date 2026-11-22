"""Keyword/rule document classification. No LLM call needed."""
from typing import Dict, List, Tuple

from schemas import Classification
from utils import normalise

# (phrase, weight). Weights reflect how strongly a phrase pins the type down.
RULES: Dict[str, Dict] = {
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
        ],
    },
    "loan_agreement": {
        "label": "Loan agreement",
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
            ("invoice", 2),
            ("consultation charges", 4),
            ("room rent", 3),
            ("pharmacy", 3),
            ("laboratory", 2),
            ("investigation charges", 3),
            ("total payable", 2),
            ("ip no", 3),
            ("uhid", 4),
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
        ],
    },
}

# Below this score the type is reported as uncertain.
CERTAIN_SCORE = 8
# And it must beat the runner-up by this much.
CERTAIN_MARGIN = 3


def score_types(text: str) -> List[Tuple[str, int, List[str]]]:
    haystack = normalise(text)
    results: List[Tuple[str, int, List[str]]] = []
    for doc_type, rule in RULES.items():
        score = 0
        matched: List[str] = []
        for phrase, weight in rule["terms"]:
            hits = haystack.count(phrase)
            if hits:
                # Repeats add evidence, but with sharply diminishing returns.
                score += weight + min(hits - 1, 3)
                matched.append(phrase)
        if score:
            results.append((doc_type, score, matched))
    results.sort(key=lambda row: row[1], reverse=True)
    return results


def classify(text: str) -> Classification:
    if not text.strip():
        return Classification(
            doc_type="other",
            label="Document type uncertain",
            certain=False,
            score=0,
            matched_terms=[],
        )

    ranked = score_types(text)
    if not ranked:
        return Classification(
            doc_type="other",
            label="Document type uncertain",
            certain=False,
            score=0,
            matched_terms=[],
        )

    doc_type, score, matched = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0
    certain = score >= CERTAIN_SCORE and (score - runner_up) >= CERTAIN_MARGIN
    label = RULES[doc_type]["label"]
    if not certain:
        return Classification(
            doc_type=doc_type,
            label="Document type uncertain (closest match: %s)" % label.lower(),
            certain=False,
            score=score,
            matched_terms=matched[:8],
        )
    return Classification(
        doc_type=doc_type,
        label=label,
        certain=True,
        score=score,
        matched_terms=matched[:8],
    )
