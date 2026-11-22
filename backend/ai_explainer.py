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
from utils import looks_malayalam, truncate

_MALAYALAM_ALTERNATIVES = ("gemma2:9b", "qwen2.5:7b", "aya:8b")


def malayalam_failed_message(model: str = "") -> str:
    """Explain the rejection, suggesting models other than the one in use."""
    model = model or config.model_for("ml")
    current = model.strip().lower()
    others = [m for m in _MALAYALAM_ALTERNATIVES if m.lower() != current]
    return (
        'The model "%s" did not reply in Malayalam, so its answer was discarded '
        "rather than shown to you as a translation. Malayalam is hard for small "
        "local models. English explanations still work, and the facts, clauses "
        "and deadlines below come from the rule engine, not the model. To try "
        "another model, set OLLAMA_MODEL in .env (for example %s) and restart "
        "the backend." % (model, " or ".join(others[:2]))
    )

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
    # Asked for Malayalam, got something else: reject it rather than present
    # another language as if it were the translation the user asked for.
    if language == "ml":
        body = " ".join(
            [
                explanation.plain_meaning,
                explanation.what_it_says,
                explanation.why_pay_attention,
            ]
        )
        if not looks_malayalam(body):
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

    budget = config.max_explained_for(language)
    chosen = _pick(clauses, budget)
    skipped = len(clauses) - len(chosen)

    llm_ok = False
    model = config.model_for(language)
    explanations: Dict[int, ClauseExplanation] = {}
    entries: List[Dict] = []
    try:
        payload = ollama_service.generate_json(
            prompts.clause_batch_prompt(
                doc_type_label,
                [_as_prompt_clause(c) for c in chosen],
                language,
                _facts_line(facts),
            ),
            system=prompts.SYSTEM,
            num_predict=config.clause_token_budget_for(language) * max(1, len(chosen)),
            model=model,
            retries=0,
            timeout=config.timeout_for(language),
        )
        candidate = payload.get("explanations")
        if isinstance(payload, dict) and not isinstance(candidate, list):
            # Some small models return a bare object for a single clause.
            candidate = [payload] if "plain_meaning" in payload else []
        entries = candidate or []
    except ollama_service.OllamaBadJson as exc:
        # Usually the reply was cut off by the token limit. Regenerating
        # truncates at the same place, so keep the complete entries instead.
        entries = [e for e in ollama_service.salvage_json_objects(exc.raw) if "id" in e]
        if entries:
            warnings.append(
                "The model's reply was cut short, so %d of %d clauses were "
                "recovered from it. Raise CLAUSE_TOKEN_BUDGET or lower "
                "MAX_EXPLAINED_CLAUSES for complete answers."
                % (len(entries), len(chosen))
            )
        else:
            warnings.append(str(exc))
    except ollama_service.OllamaUnavailable as exc:
        warnings.append(str(exc))
    except ollama_service.OllamaError as exc:
        warnings.append(str(exc))

    # Parsing runs for a clean reply and a salvaged one alike.
    if entries:
        wrong_language = 0
        for position, entry in enumerate(entries):
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
            elif language == "ml":
                wrong_language += 1
        llm_ok = bool(explanations)
        if not llm_ok and wrong_language:
            warnings.append(malayalam_failed_message(model))
        elif not llm_ok:
            warnings.append(
                "The local model replied but no usable explanation could be read from "
                "it. Rule-based notes are shown instead. A larger OLLAMA_MODEL usually "
                "fixes this."
            )

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
            "(limit %d for this language). The remaining %d show rule-based notes."
            % (len(chosen), budget, skipped)
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
            model=config.model_for(language),
            timeout=config.timeout_for(language),
        )
        summary = str(payload.get("summary", "") or "").strip()
        if summary and language == "ml" and not looks_malayalam(summary):
            return fallback, "rules", [malayalam_failed_message()]
        if summary:
            return summary, "llm", []
        return fallback, "rules", ["The model returned an empty summary."]
    except ollama_service.OllamaError as exc:
        return fallback, "rules", [str(exc)]
