"""Document-grounded Q&A.

Retrieval is a small TF-IDF scorer written by hand: a few dozen lines, no
vector database, no extra dependency. Only the top excerpts go to Ollama, so
a long document costs the same as a short one.
"""
import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

import config
import ollama_service
import prompts
from schemas import AskResponse, Evidence, Segment
from utils import truncate

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9]+|[ഀ-ൿ]+")

STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "has", "have", "how", "i", "if", "in", "is", "it", "its", "me",
    "much", "my", "of", "on", "or", "shall", "should", "so", "that", "the", "there",
    "they", "this", "to", "upon", "was", "what", "when", "which", "who", "will",
    "with", "would", "you", "your",
}

# Question wording -> document wording. Helps when the user says "deposit"
# but the contract says "caution deposit", or asks about "leaving early".
SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "deposit": ("deposit", "advance", "caution", "security"),
    "rent": ("rent", "licence", "license", "lease"),
    "notice": ("notice", "intimation", "inform"),
    "terminate": ("terminate", "termination", "vacate", "quit", "surrender", "cancel"),
    "early": ("early", "premature", "before", "prior"),
    "charge": ("charge", "charges", "fee", "fees", "cost", "payable"),
    "extra": ("extra", "additional", "over", "above", "separate"),
    "penalty": ("penalty", "penal", "fine", "damages", "late"),
    "interest": ("interest", "rate", "annum"),
    "emi": ("emi", "instalment", "installment", "monthly"),
    "loan": ("loan", "principal", "facility", "sanctioned"),
    "deadline": ("deadline", "last", "before", "within", "failing"),
    "due": ("due", "payable", "before"),
    "period": ("period", "term", "duration", "tenure", "months", "years"),
    "total": ("total", "grand", "net", "payable", "amount"),
    "refund": ("refund", "refundable", "return", "deduct"),
    "increase": ("increase", "escalation", "hike", "revise", "revised"),
}


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def expand(tokens: List[str]) -> List[str]:
    out = list(tokens)
    for token in tokens:
        out.extend(SYNONYMS.get(token, ()))
    return out


def rank_segments(
    question: str, segments: List[Segment], top_k: int = 5
) -> List[Tuple[Segment, float]]:
    """TF-IDF cosine-ish scoring over segments. Nothing heavier is needed."""
    if not segments:
        return []

    docs = [tokenize(s.text) for s in segments]
    total = len(docs)
    doc_freq: Counter = Counter()
    for tokens in docs:
        doc_freq.update(set(tokens))

    def idf(term: str) -> float:
        return math.log((total + 1) / (doc_freq.get(term, 0) + 1)) + 1.0

    query_tokens = expand(tokenize(question))
    if not query_tokens:
        return []
    query_weights = Counter(query_tokens)

    scored: List[Tuple[Segment, float]] = []
    for segment, tokens in zip(segments, docs):
        if not tokens:
            continue
        counts = Counter(tokens)
        length = math.sqrt(sum(v * v for v in counts.values())) or 1.0
        score = 0.0
        for term, weight in query_weights.items():
            if term in counts:
                score += weight * counts[term] * (idf(term) ** 2)
        score /= length
        if score > 0:
            scored.append((segment, score))

    scored.sort(key=lambda row: row[1], reverse=True)
    return scored[:top_k]


# Below this the best match is too weak to call evidence.
MIN_SCORE = 0.35


def answer_question(
    question: str,
    segments: List[Segment],
    doc_type_label: str,
    language: str = "en",
) -> AskResponse:
    ranked = rank_segments(question, segments, top_k=5)
    if not ranked or ranked[0][1] < MIN_SCORE:
        return AskResponse(
            answer=prompts.not_found_message(language),
            evidence=[],
            grounded=False,
            source="rules",
            language=language,
        )

    evidence = [
        Evidence(text=truncate(segment.text, 400), page=segment.page, score=round(score, 3))
        for segment, score in ranked
    ]

    excerpts: List[Dict] = []
    budget = config.MAX_QA_CONTEXT_CHARS
    for segment, _score in ranked:
        text = truncate(segment.text, 600)
        if budget - len(text) < 0:
            break
        budget -= len(text)
        excerpts.append({"text": text, "page": segment.page})

    try:
        payload = ollama_service.generate_json(
            prompts.qa_prompt(question, doc_type_label, excerpts, language),
            system=prompts.SYSTEM,
            num_predict=400,
        )
        answer = str(payload.get("answer", "") or "").strip()
        found = payload.get("found")
        if not answer:
            raise ollama_service.OllamaError("The model returned an empty answer.")
        grounded = bool(found) if isinstance(found, bool) else True
        return AskResponse(
            answer=answer,
            evidence=evidence if grounded else [],
            grounded=grounded,
            source="llm",
            language=language,
        )
    except ollama_service.OllamaError as exc:
        # No model: hand back the matching sentences themselves. That is
        # evidence from the document, not a generated answer.
        lead = (
            "The local AI model is unavailable, so here are the closest matching "
            "sentences from your document. %s" % exc
        )
        return AskResponse(
            answer=lead,
            evidence=evidence,
            grounded=True,
            source="rules",
            language=language,
        )
