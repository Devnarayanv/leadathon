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
        '"%s" മോഡൽ മലയാളത്തിൽ മറുപടി നൽകിയില്ല, അതിനാൽ ആ ഉത്തരം വിവർത്തനമായി '
        "കാണിക്കാതെ ഒഴിവാക്കി. ചെറിയ ലോക്കൽ മോഡലുകൾക്ക് മലയാളം ബുദ്ധിമുട്ടാണ്. "
        "താഴെയുള്ള വിവരങ്ങളും വാക്യങ്ങളും തീയതികളും മോഡലിൽ നിന്നല്ല, ചട്ട "
        "എൻജിനിൽ നിന്നാണ്. മറ്റൊരു മോഡൽ പരീക്ഷിക്കാൻ .env-ൽ OLLAMA_MODEL "
        "സെറ്റ് ചെയ്ത് (ഉദാ: %s) ബാക്കെൻഡ് പുനരാരംഭിക്കുക."
        % (model, " അല്ലെങ്കിൽ ".join(others[:2]))
    )

def _english_wrong_language_message(model: str) -> str:
    return (
        'The model "%s" did not reply in Malayalam, so its answer was discarded '
        "rather than shown as a translation." % (model or config.model_for("ml"))
    )


def _ollama_warning(exc: Exception, language: str = "en") -> str:
    """The model-side reason, in the language the user is reading.

    Ollama's own messages are English and fairly technical. Translating the
    class of failure keeps the note useful without pretending to quote it.
    """
    if language != "ml":
        return str(exc)
    model = config.model_for("ml")
    if isinstance(exc, ollama_service.OllamaUnavailable):
        return (
            "Ollama ലഭ്യമല്ല അല്ലെങ്കിൽ \"%s\" മോഡൽ ഇൻസ്റ്റാൾ ചെയ്തിട്ടില്ല. "
            "അതിനാൽ താഴെയുള്ളത് ചട്ടങ്ങളിസ്ഥാനമാക്കിയുള്ള കുറിപ്പുകളാണ്. "
            "Ollama ആരംഭിച്ച് `ollama pull %s` ചെയ്താൽ AI വിശദീകരണം "
            "ലഭിക്കും." % (model, model)
        )
    if isinstance(exc, ollama_service.OllamaBadJson):
        return (
            "ലോക്കൽ മോഡൽ സാധുവായ JSON നൽകിയില്ല. മറ്റൊരു OLLAMA_MODEL "
            "പരീക്ഷിക്കുക; അതുവരെ ചട്ടങ്ങളടിസ്ഥാനമാക്കിയുള്ള കുറിപ്പുകൾ "
            "കാണിക്കുന്നു."
        )
    return (
        "ഈ അഭ്യർത്ഥന പൂർത്തിയാക്കാൻ ലോക്കൽ മോഡലിന് കഴിഞ്ഞില്ല. "
        "ചട്ടങ്ങളടിസ്ഥാനമാക്കിയുള്ള കുറിപ്പുകൾ കാണിക്കുന്നു."
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
            if language == "ml":
                warnings.append(
                    "മോഡലിന്റെ മറുപടി നടുവിൽ മുറിഞ്ഞു, %d-ൽ %d വാക്യങ്ങൾ "
                    "അതിൽ നിന്ന് കണ്ടെടുത്തു. പൂർണ്ണ ഉത്തരങ്ങൾക്ക് "
                    "CLAUSE_TOKEN_BUDGET കൂട്ടുകയോ MAX_EXPLAINED_CLAUSES "
                    "കുറയ്ക്കുകയോ ചെയ്യുക." % (len(entries), len(chosen))
                )
            else:
                warnings.append(
                    "The model's reply was cut short, so %d of %d clauses were "
                    "recovered from it. Raise CLAUSE_TOKEN_BUDGET or lower "
                    "MAX_EXPLAINED_CLAUSES for complete answers."
                    % (len(entries), len(chosen))
                )
        else:
            warnings.append(_ollama_warning(exc, language))
    except ollama_service.OllamaUnavailable as exc:
        warnings.append(_ollama_warning(exc, language))
    except ollama_service.OllamaError as exc:
        warnings.append(_ollama_warning(exc, language))

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
            warnings.append(
                malayalam_failed_message(model)
                if language == "ml"
                else _english_wrong_language_message(model)
            )
        elif not llm_ok:
            warnings.append(
                "ലോക്കൽ മോഡൽ മറുപടി നൽകി, പക്ഷേ അതിൽ നിന്ന് ഉപയോഗിക്കാവുന്ന "
                "വിശദീകരണം കിട്ടിയില്ല. പകരം ചട്ടങ്ങളടിസ്ഥാനമാക്കിയുള്ള "
                "കുറിപ്പുകൾ കാണിക്കുന്നു. വലിയ OLLAMA_MODEL സാധാരണ ഇത് "
                "പരിഹരിക്കും."
                if language == "ml"
                else "The local model replied but no usable explanation could be read "
                "from it. Rule-based notes are shown instead. A larger OLLAMA_MODEL "
                "usually fixes this."
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
            "%d വാക്യത്തിന് മോഡലിൽ നിന്ന് വിശദീകരണം ലഭിച്ചില്ല; അവയ്ക്ക് "
            "ചട്ടങ്ങളടിസ്ഥാനമാക്കിയുള്ള കുറിപ്പുകൾ കാണിക്കുന്നു." % missing
            if language == "ml"
            else "%d clause(s) came back without an explanation from the model; "
            "rule-based notes are shown for those." % missing
        )
    if skipped > 0 and llm_ok:
        warnings.append(
            "ഏറ്റവും പ്രധാനപ്പെട്ട %d വാക്യങ്ങൾക്ക് AI വിശദീകരണം "
            "തയ്യാറാക്കി (ഈ ഭാഷയ്ക്ക് പരിധി %d). ബാക്കിയുള്ള %d ചട്ടങ്ങളടിസ്ഥാനമാക്കിയുള്ള "
            "കുറിപ്പുകൾ കാണിക്കുന്നു." % (len(chosen), budget, skipped)
            if language == "ml"
            else "AI explanations were generated for the %d highest-priority clauses "
            "(limit %d for this language). The remaining %d show rule-based notes."
            % (len(chosen), budget, skipped)
        )
    return clauses, warnings


def rule_summary(
    doc_type_label: str, facts: List[Fact], clauses: List[Clause], language: str = "en"
) -> str:
    """Summary built from rule output only. Always truthful, never invented."""
    categories = []
    for clause in clauses:
        if clause.label not in categories:
            categories.append(clause.label)

    if language == "ml":
        parts = ["കണ്ടെത്തിയ രേഖാ തരം: %s." % doc_type_label]
        if facts:
            parts.append(
                "രേഖയിൽ നിന്ന് വായിച്ച പ്രധാന വിവരങ്ങൾ: "
                + "; ".join("%s = %s" % (f.label, f.value) for f in facts[:4])
                + "."
            )
        else:
            parts.append("ചട്ട എൻജിനിൽ നിന്ന് പ്രധാന വിവരങ്ങൾ വായിക്കാനായില്ല.")
        if clauses:
            parts.append(
                "%d വാക്യം ശ്രദ്ധയ്ക്കായി അടയാളപ്പെടുത്തി: %s."
                % (len(clauses), ", ".join(categories[:5]))
            )
        else:
            parts.append("ശ്രദ്ധാ ചട്ടങ്ങളുമായി ഒരു വാക്യവും പൊരുത്തപ്പെട്ടില്ല.")
        return " ".join(parts)

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
    fallback = rule_summary(doc_type_label, facts, clauses, language)
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
        return fallback, "rules", [
            "മോഡൽ ശൂന്യമായ ചുരുക്കം നൽകി."
            if language == "ml"
            else "The model returned an empty summary."
        ]
    except ollama_service.OllamaError as exc:
        return fallback, "rules", [_ollama_warning(exc, language)]
