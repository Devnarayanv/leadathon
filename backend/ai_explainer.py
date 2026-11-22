"""Clause explanations and the document summary, via one batched Ollama call.

The rule engine already decided what matters. The model only rewrites those
clauses in plain language. When Ollama is down, rule templates fill in and the
response says so: nothing is faked.
"""
import logging
from typing import Dict, List, Optional, Tuple

import clause_detector
import config
import ollama_service
import prompts
from schemas import Clause, ClauseExplanation, Fact
from utils import truncate

logger = logging.getLogger(__name__)


def _facts_line(facts: List[Fact], limit: int = 6) -> str:
    return "; ".join("%s: %s" % (f.label, f.value) for f in facts[:limit])


def _as_prompt_clause(clause: Clause) -> Dict:
    return {
        "id": clause.id,
        "label": clause.label,
        "page": clause.page,
        "reason": clause.reason,
        "text": truncate(clause.text, config.MAX_CLAUSE_CHARS),
    }


def _pick(clauses: List[Clause], budget: int) -> List[Clause]:
    """Highest-priority clauses first; detect_clauses already sorted them."""
    return clauses[:budget]


def _coerce(entry: Dict, language: str) -> Optional[ClauseExplanation]:
    try:
        explanation = ClauseExplanation(
            what_it_says=str(entry.get("what_it_says", "") or "").strip(),
            plain_meaning=str(entry.get("plain_meaning", "") or "").strip(),
            why_pay_attention=str(entry.get("why_pay_attention", "") or "").strip(),
            next_step=str(entry.get("next_step", "") or "").strip(),
            uncertain=str(entry.get("uncertain", "") or "").strip(),
            source="llm",
            language=language,
        )
    except Exception as exc:  # pragma: no cover - pydantic guards the types
        logger.warning("Rejected malformed explanation entry: %s", exc)
        return None
    # An entry with no usable content is worse than the rule template.
    if not (explanation.plain_meaning or explanation.what_it_says):
        return None
    return explanation


def explain_clauses(
    clauses: List[Clause],
    doc_type_label: str,
    facts: List[Fact],
    language: str = "en",
) -> Tuple[List[Clause], List[str]]:
    """Fill clause.explanation in place-ish. Returns (clauses, warnings)."""
    warnings: List[str] = []
    if not clauses:
        return clauses, warnings

    chosen = _pick(clauses, config.MAX_EXPLAINED_CLAUSES)
    skipped = len(clauses) - len(chosen)

    llm_ok = False
    explanations: Dict[int, ClauseExplanation] = {}
    try:
        payload = ollama_service.generate_json(
            prompts.clause_batch_prompt(
                doc_type_label,
                [_as_prompt_clause(c) for c in chosen],
                language,
                _facts_line(facts),
            ),
            system=prompts.SYSTEM,
            num_predict=260 * max(1, len(chosen)),
        )
        entries = payload.get("explanations")
        if isinstance(payload, dict) and not isinstance(entries, list):
            # Some small models return a bare object for a single clause.
            entries = [payload] if "plain_meaning" in payload else []
        for position, entry in enumerate(entries or []):
            if not isinstance(entry, dict):
                continue
            raw_id = entry.get("id")
            try:
                clause_id = int(raw_id)
            except (TypeError, ValueError):
                clause_id = chosen[position].id if position < len(chosen) else -1
            explanation = _coerce(entry, language)
            if explanation:
                explanations[clause_id] = explanation
        llm_ok = bool(explanations)
        if not llm_ok:
            warnings.append(
                "The local model replied but no usable explanation could be read from "
                "it. Rule-based notes are shown instead. A larger OLLAMA_MODEL usually "
                "fixes this."
            )
    except ollama_service.OllamaUnavailable as exc:
        warnings.append(str(exc))
    except ollama_service.OllamaError as exc:
        warnings.append(str(exc))

    missing = 0
    chosen_ids = {c.id for c in chosen}
    for clause in clauses:
        explanation = explanations.get(clause.id)
        if explanation:
            clause.explanation = explanation
            continue
        if clause.id in chosen_ids and llm_ok:
            missing += 1
        clause.explanation = ClauseExplanation(
            **clause_detector.rule_explanation(clause, language),
            source="rules",
            language=language,
        )

    if missing:
        warnings.append(
            "%d clause(s) came back without an explanation from the model; rule-based "
            "notes are shown for those." % missing
        )
    if skipped > 0 and llm_ok:
        warnings.append(
            "AI explanations were generated for the %d highest-priority clauses "
            "(MAX_EXPLAINED_CLAUSES=%d). The remaining %d show rule-based notes."
            % (len(chosen), config.MAX_EXPLAINED_CLAUSES, skipped)
        )
    return clauses, warnings


def rule_summary(doc_type_label: str, facts: List[Fact], clauses: List[Clause]) -> str:
    """Summary built from rule output only. Always truthful, never invented."""
    parts = ["Detected document type: %s." % doc_type_label]
    if facts:
        parts.append(
            "Key values read from the document: "
            + "; ".join("%s = %s" % (f.label, f.value) for f in facts[:4])
            + "."
        )
    else:
        parts.append("No key values could be read by the rule engine.")
    if clauses:
        categories = []
        for clause in clauses:
            if clause.label not in categories:
                categories.append(clause.label)
        parts.append(
            "%d clause(s) were flagged for attention, covering: %s."
            % (len(clauses), ", ".join(categories[:5]))
        )
    else:
        parts.append("No clauses matched the attention rules.")
    return " ".join(parts)


def build_summary(
    doc_type_label: str,
    facts: List[Fact],
    clauses: List[Clause],
    language: str = "en",
) -> Tuple[str, str, List[str]]:
    """Returns (summary, source, warnings)."""
    fallback = rule_summary(doc_type_label, facts, clauses)
    highlights = ["%s: %s" % (f.label, f.value) for f in facts[:6]]
    highlights += ["Flagged - %s: %s" % (c.label, truncate(c.text, 160)) for c in clauses[:5]]
    if not highlights:
        return fallback, "rules", []

    try:
        payload = ollama_service.generate_json(
            prompts.summary_prompt(doc_type_label, language, highlights),
            system=prompts.SYSTEM,
            num_predict=300,
        )
        summary = str(payload.get("summary", "") or "").strip()
        if summary:
            return summary, "llm", []
        return fallback, "rules", ["The model returned an empty summary."]
    except ollama_service.OllamaError as exc:
        return fallback, "rules", [str(exc)]
