"""Evidence-first findings, and the action list built from them.

A finding is made only from something the document or the arithmetic produced:
a deadline the extractor found, a clause the rules matched, a verification check
that disagreed, or a field the type expects but the text does not state. Each
carries the original wording and page so the user can check it.

Action items are built from findings only and point back with finding_ref.
"""
from typing import Dict, List, Sequence, Tuple

from doc_intel import REQUIRED_FIELDS
from schemas import ActionItem, Clause, Deadline, Fact, Finding, VerificationReport

MAX_CLAUSE_FINDINGS = 8
MAX_MISSING_FINDINGS = 6

_CLAUSE_CATEGORY = {
    "financial": ("financial_obligation", "high"),
    "unusual": ("important_condition", "medium"),
    "attention": ("important_condition", "medium"),
}


def build(
    doc_type: str,
    facts: Sequence[Fact],
    deadlines: Sequence[Deadline],
    clauses: Sequence[Clause],
    verification: VerificationReport,
) -> Tuple[List[Finding], List[ActionItem]]:
    findings: List[Finding] = []
    due: Dict[str, Tuple[str | None, str | None]] = {}

    def add(**fields) -> Finding:
        number = len(findings) + 1
        finding = Finding(id=number, ref="F%d" % number, **fields)
        findings.append(finding)
        return finding

    for deadline in deadlines:
        finding = add(
            title="Deadline: %s" % deadline.date_text,
            category="deadline",
            severity="medium" if deadline.needs_verification or not deadline.date_iso else "high",
            evidence_status=deadline.evidence_status,
            original_text=deadline.source_text,
            page=deadline.page,
            explanation='The document ties the date "%s" to: %s' % (deadline.date_text, deadline.description),
            why_it_matters="The document sets this date for an action. Missing it may carry the consequence the document describes.",
            suggested_action=(
                "Check the date against the document, then add it to your calendar."
                + (" The date was worked out from the wording, so confirm it." if deadline.needs_verification else "")
            ),
            confidence=deadline.confidence,
        )
        due[finding.ref] = (deadline.date_iso, deadline.date_text)

    clause_findings = 0
    for clause in clauses:
        mapped = _CLAUSE_CATEGORY.get(clause.attention_level)
        if mapped is None:
            continue
        if clause_findings >= MAX_CLAUSE_FINDINGS:
            break
        clause_findings += 1
        category, severity = mapped
        add(
            title=clause.label,
            category=category,
            severity=severity,
            evidence_status="extracted",
            original_text=clause.text[:400],
            page=clause.page,
            explanation=clause.reason,
            why_it_matters="Flagged because it matches the rule for: %s." % clause.label,
            suggested_action=clause.suggested_action or "Read this clause in full before you sign or pay.",
            confidence=clause.confidence,
        )

    for check in verification.checks:
        if check.status not in ("mismatch", "needs_attention"):
            continue
        add(
            title="Figures disagree: %s" % check.label,
            category="verification_required",
            severity="high" if check.status == "mismatch" else "medium",
            evidence_status="calculated",
            original_text=check.source_text or "",
            page=check.page,
            explanation=check.explanation,
            why_it_matters="The document's own figures do not agree, so one of them may be wrong.",
            suggested_action="Ask the issuer to confirm the figure before you pay or sign.",
            confidence="high",
        )

    present = {fact.key for fact in facts}
    missing_count = 0
    for key, label in REQUIRED_FIELDS.get(doc_type, []):
        if key in present:
            continue
        if missing_count >= MAX_MISSING_FINDINGS:
            break
        missing_count += 1
        add(
            title="Not stated: %s" % label,
            category="missing_information",
            severity="low",
            evidence_status="needs_verification",
            original_text="",
            page=None,
            explanation="This document does not state a %s in text Doc Decode can read. It has not been filled in." % label.lower(),
            why_it_matters="Some checks and comparisons need this value.",
            suggested_action="Check whether the %s is on another page or in another document." % label.lower(),
            confidence="high",
        )

    actions: List[ActionItem] = []
    for finding in findings:
        if not (finding.category in ("deadline", "financial_obligation", "verification_required")
                or finding.severity == "high"):
            continue
        iso, text = due.get(finding.ref, (None, None))
        actions.append(
            ActionItem(
                id=len(actions) + 1,
                title=finding.title,
                detail=finding.suggested_action,
                due_date_iso=iso,
                due_date_text=text,
                page=finding.page,
                source_text=finding.original_text,
                finding_ref=finding.ref,
                priority=finding.severity,
            )
        )
    return findings, actions
