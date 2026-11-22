"""Rule-based clause detection.

These are attention indicators, not legal judgments. Nothing here says a
clause is illegal, void or fraudulent; the labels only mean "a person signing
this should read this sentence carefully".

Each rule needs a primary phrase AND, where the phrase is ambiguous on its
own, a supporting phrase. Negative phrases veto a match. That keeps the
engine from flagging "the notice board in the lobby" as a notice period.
"""
import re
from typing import Dict, List, Optional, Sequence

import dates
from schemas import Clause, Segment
from utils import normalise, segment_context, truncate

# Shortest/longest sentence worth flagging.
MIN_LEN = 25
MAX_LEN = 1200

RULES: List[Dict] = [
    {
        "category": "auto_renewal",
        "label": "Auto-renewal",
        "attention_level": "attention",
        "primary": [
            "automatically renew", "automatically be renewed", "auto-renew",
            "auto renewal", "deemed to be renewed", "deemed renewed",
            "shall stand renewed", "renewed automatically",
            "unless terminated", "unless either party",
        ],
        "support": ["renew", "extend", "continue", "term"],
        "negative": ["shall not be renewed", "no automatic renewal", "cannot be renewed"],
        "reason": "The agreement may continue by itself unless somebody acts in time.",
        "action": "Note the last date to give notice if you do not want it to continue.",
        "requires_support_for": ["unless terminated", "unless either party"],
    },
    {
        "category": "penalty",
        "label": "Penalty charge",
        "attention_level": "financial",
        "primary": [
            "penalty", "penal interest", "penal charge", "liquidated damages",
            "shall be liable to pay a fine", "fine of rs",
        ],
        "support": [],
        "negative": ["no penalty", "without penalty", "penalty free", "waive the penalty"],
        "reason": "A money penalty applies in the situation this sentence describes.",
        "action": "Ask exactly when the penalty starts and how it is calculated.",
    },
    {
        "category": "late_payment",
        "label": "Late-payment fee",
        "attention_level": "financial",
        "primary": [
            "late payment", "late fee", "delayed payment", "overdue",
            "not paid on or before", "default in payment", "fails to pay",
            "delay in payment",
        ],
        "support": [],
        "negative": ["no late fee", "without any late fee"],
        "reason": "Paying late costs extra money or triggers another consequence.",
        "action": "Confirm the exact due date and the grace period, if any.",
    },
    {
        "category": "extra_charges",
        "label": "Additional charges",
        "attention_level": "financial",
        "primary": [
            "additional charge", "extra charge", "over and above", "in addition to the rent",
            "maintenance charge", "service charge", "processing fee", "documentation charge",
            "administrative charge", "shall be borne by", "at the cost of the",
            "payable separately", "excluding",
        ],
        "support": ["pay", "charge", "fee", "cost", "borne", "rs", "amount", "%"],
        "negative": ["no additional charge", "no extra charge", "inclusive of all charges"],
        "reason": "Money is due beyond the headline amount.",
        "action": "Add these charges up and ask for the full monthly or total cost in writing.",
        "requires_support_for": ["shall be borne by", "at the cost of the", "excluding"],
    },
    {
        "category": "lock_in",
        "label": "Lock-in period",
        "attention_level": "unusual",
        "primary": [
            "lock-in", "lock in period", "minimum period of", "shall not vacate before",
            "cannot terminate before", "minimum commitment",
        ],
        "support": ["month", "year", "period", "term", "day"],
        "negative": ["no lock-in", "without any lock-in"],
        "reason": "You may be committed for a fixed stretch even if you want to leave.",
        "action": "Check what you owe if you have to leave during this period.",
        "requires_support_for": ["minimum period of", "minimum commitment"],
    },
    {
        "category": "early_termination",
        "label": "Early termination",
        "attention_level": "attention",
        "primary": [
            "early termination", "terminate the agreement before", "premature termination",
            "foreclosure", "pre-closure", "prepayment charge", "pre-payment charge",
            "vacate before the expiry", "terminate this agreement",
        ],
        "support": [],
        "negative": [],
        "reason": "Ending the arrangement early has its own conditions or cost.",
        "action": "Work out the cost of leaving early before you sign.",
    },
    {
        "category": "deposit_deduction",
        "label": "Deduction or forfeiture",
        "attention_level": "financial",
        "primary": [
            "deduct", "deducted from the deposit", "forfeit", "forfeited",
            "adjust against the deposit", "set off against the deposit",
            "non-refundable",
        ],
        "support": ["deposit", "advance", "amount", "rent", "security"],
        "negative": ["shall not be deducted", "fully refundable", "refunded in full"],
        "reason": "Money you have already paid can be kept back or reduced.",
        "action": "Ask for the deduction heads in writing and photograph the property or asset condition.",
        "requires_support_for": ["deduct", "forfeit", "forfeited", "non-refundable"],
    },
    {
        "category": "notice_period",
        "label": "Notice period",
        "attention_level": "attention",
        "primary": [
            "notice period", "months notice", "month notice", "months prior notice",
            "days notice", "days prior notice", "written notice of", "prior written notice",
            "advance notice of", "serve a notice",
        ],
        "support": ["day", "month", "year", "week", "terminate", "vacate", "quit"],
        "negative": ["no notice is required", "without notice period"],
        "reason": "You must tell the other side a set time in advance.",
        "action": "Mark the latest date you can still give valid notice.",
        "requires_support_for": ["written notice of", "prior written notice", "serve a notice"],
    },
    {
        "category": "interest_rate",
        "label": "Interest condition",
        "attention_level": "financial",
        "primary": [
            "rate of interest", "interest at the rate", "per annum", "compounded",
            "floating rate", "reset the interest", "revise the interest",
            "interest shall be charged",
        ],
        "support": [],
        "negative": ["interest free", "no interest shall be charged"],
        "reason": "Interest terms decide how much the total actually costs.",
        "action": "Ask whether the rate can change, and what the total repayment comes to.",
    },
    {
        "category": "obligation",
        "label": "Important obligation",
        "attention_level": "attention",
        "primary": [
            "shall be responsible for", "shall be liable for", "undertakes to",
            "at his own cost", "at her own cost", "at their own cost", "at own expense",
            "shall indemnify", "shall maintain", "shall not sublet", "shall not assign",
            "shall keep the", "obliged to",
        ],
        "support": [],
        "negative": [],
        "reason": "This sentence puts a duty on one side.",
        "action": "Check the duty is one you can actually meet.",
    },
    {
        "category": "deadline",
        "label": "Important deadline",
        "attention_level": "deadline",
        "primary": [
            "on or before", "no later than", "not later than", "failing which",
            "last date", "within a period of", "within", "due on", "due date",
            "expire on", "expires on",
        ],
        "support": [],
        "negative": [],
        "reason": "A date or time limit applies here.",
        "action": "Put this date in your calendar with a reminder a few days earlier.",
        # "within"/"due date" alone is weak: a date or duration must be present too.
        "requires_date_for": ["within", "due date", "due on", "last date"],
    },
    {
        "category": "unusual_condition",
        "label": "One-sided condition",
        "attention_level": "unusual",
        "primary": [
            "sole discretion", "absolute discretion", "without assigning any reason",
            "without any notice", "waives all rights", "waive any right",
            "shall be final and binding", "not be liable for any",
            "irrevocably", "unconditionally", "at any time without",
            "shall have the right to enter", "disconnect the supply",
        ],
        "support": [],
        "negative": [],
        "reason": "The sentence gives one side wide power or removes a protection.",
        "action": "Ask for this to be made mutual, or get it explained in writing.",
    },
]

# Categories that get priority when the explanation budget is small.
PRIORITY = {
    "unusual_condition": 0,
    "deposit_deduction": 1,
    "penalty": 2,
    "auto_renewal": 3,
    "lock_in": 4,
    "late_payment": 5,
    "extra_charges": 6,
    "early_termination": 7,
    "interest_rate": 8,
    "notice_period": 9,
    "deadline": 10,
    "obligation": 11,
}

_LEVEL_LABELS = {
    "attention": "Attention required",
    "financial": "Financial condition",
    "deadline": "Important deadline",
    "unusual": "Unusual condition",
    "info": "For information",
}


def level_label(level: str) -> str:
    return _LEVEL_LABELS.get(level, "Attention required")


def _hits(haystack: str, phrases: Sequence[str]) -> List[str]:
    return [p for p in phrases if p in haystack]


def _confidence(rule: Dict, matched: List[str], support: List[str], text: str) -> str:
    strong = len(matched) > 1 or len(max(matched, key=len)) > 18
    if strong and (support or not rule.get("support")):
        return "high"
    if matched and support:
        return "high" if strong else "medium"
    if matched and not rule.get("support"):
        return "medium"
    return "low"


def _rule_reason(rule: Dict, matched: List[str]) -> str:
    quoted = ", ".join('"%s"' % m for m in matched[:3])
    return "%s Matched wording: %s." % (rule["reason"], quoted)


# Most sentences a single category may contribute. Past this the dashboard is
# noise: three examples of "penalty" make the point, nine do not.
MAX_PER_CATEGORY = 2


def detect_clauses(
    segments: List[Segment],
    doc_type: str = "other",
    max_clauses: int = 25,
    max_per_category: int = MAX_PER_CATEGORY,
) -> List[Clause]:
    """Scan every segment against every rule.

    A sentence yields at most one clause per category, a category yields at
    most max_per_category sentences, and the document is capped at
    max_clauses, so a 40-page contract cannot flood the dashboard.
    """
    clauses: List[Clause] = []
    next_id = 1
    seen: set = set()

    for index, segment in enumerate(segments):
        text = segment.text.strip()
        if not (MIN_LEN <= len(text) <= MAX_LEN):
            continue
        haystack = normalise(text)

        for rule in RULES:
            matched = _hits(haystack, rule["primary"])
            if not matched:
                continue
            if _hits(haystack, rule.get("negative", [])):
                continue

            support = _hits(haystack, rule.get("support", []))
            needs_support = [m for m in matched if m in rule.get("requires_support_for", [])]
            if needs_support and len(needs_support) == len(matched) and not support:
                continue

            needs_date = [m for m in matched if m in rule.get("requires_date_for", [])]
            if needs_date and len(needs_date) == len(matched):
                if not (dates.has_date(text) or dates.find_duration(text)):
                    continue

            key = (rule["category"], haystack[:90])
            if key in seen:
                continue
            seen.add(key)

            clauses.append(
                Clause(
                    id=next_id,
                    category=rule["category"],
                    label=rule["label"],
                    attention_level=rule["attention_level"],
                    text=truncate(text, MAX_LEN),
                    page=segment.page,
                    reason=_rule_reason(rule, matched),
                    confidence=_confidence(rule, matched, support, text),
                    matched_terms=matched[:4],
                    suggested_action=rule["action"],
                )
            )
            next_id += 1

    rank = {"high": 0, "medium": 1, "low": 2}
    clauses.sort(
        key=lambda c: (
            PRIORITY.get(c.category, 99),
            rank[c.confidence],
            c.page or 0,
        )
    )

    # Keep the strongest few per category (the sort above put them first).
    per_category: Dict[str, int] = {}
    kept: List[Clause] = []
    for clause in clauses:
        count = per_category.get(clause.category, 0)
        if count >= max_per_category:
            continue
        per_category[clause.category] = count + 1
        kept.append(clause)

    kept = kept[:max_clauses]
    for position, clause in enumerate(kept, start=1):
        clause.id = position
    return kept


def clause_context(segments: List[Segment], clause: Clause) -> str:
    """Neighbouring text for the clause, used as LLM context."""
    for index, segment in enumerate(segments):
        if segment.text.startswith(clause.text[:60]):
            return segment_context(segments, index, window=1)
    return clause.text


def attention_counts(clauses: List[Clause]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for clause in clauses:
        counts[clause.attention_level] = counts.get(clause.attention_level, 0) + 1
    return counts


def rule_explanation(clause: Clause, language: str = "en") -> Dict[str, str]:
    """Template explanation used when Ollama is unavailable.

    It restates the rule, never the clause's meaning: no model, no claim about
    what the sentence means beyond the matched wording.
    """
    if language == "ml":
        return {
            "what_it_says": "രേഖയിലെ ഈ വാക്യം മുകളിൽ അതേപടി നൽകിയിരിക്കുന്നു.",
            "plain_meaning": (
                "പ്രാദേശിക AI മോഡൽ ലഭ്യമല്ല, അതിനാൽ ലളിതമായ വിശദീകരണം ഇപ്പോൾ നൽകാനാകില്ല. "
                "ചട്ട പരിശോധനയിൽ ഈ വാക്യം \"%s\" എന്ന വിഭാഗത്തിൽ വരുന്നു." % clause.label
            ),
            "why_pay_attention": clause.reason,
            "next_step": clause.suggested_action,
            "uncertain": "Ollama ആരംഭിച്ച ശേഷം വീണ്ടും വിശദീകരണം ചോദിക്കുക.",
        }
    return {
        "what_it_says": "The clause is shown above exactly as it appears in the document.",
        "plain_meaning": (
            "The local AI model is not available, so no plain-language rewrite was "
            'generated. The rule engine placed this sentence under "%s".' % clause.label
        ),
        "why_pay_attention": clause.reason,
        "next_step": clause.suggested_action,
        "uncertain": "Start Ollama and ask for explanations again for a plain-language version.",
    }
