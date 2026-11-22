"""Text cleanup, segmentation and small shared helpers."""
import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Tuple

from schemas import Segment

# Characters that mangle regex / display but carry no meaning.
_INVISIBLE = dict.fromkeys(
    [0x00AD, 0x200B, 0x200C, 0x200D, 0xFEFF], None
)

_WS_RUN = re.compile(r"[ \t ]{2,}")
_BLANK_RUN = re.compile(r"\n{3,}")
# A line break that is clearly mid-sentence (lowercase/comma continues).
_SOFT_BREAK = re.compile(r"(?<=[a-z,;ഀ-ൿ])\n(?=[a-z(ഀ-ൿ])")
_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")


def clean_text(raw: str) -> str:
    """Normalise whitespace without merging separate sentences.

    Paragraph boundaries (blank lines) are preserved. Hyphenated words split
    across lines are rejoined. Mid-sentence wraps become single spaces.
    """
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", raw)
    text = text.translate(_INVISIBLE)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _SOFT_BREAK.sub(" ", text)
    text = _WS_RUN.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _BLANK_RUN.sub("\n\n", text)
    return text.strip()


# Abbreviations that must not end a sentence.
_ABBREV = (
    "no",
    "nos",
    "rs",
    "mr",
    "mrs",
    "ms",
    "dr",
    "sr",
    "jr",
    "vs",
    "etc",
    "govt",
    "ltd",
    "pvt",
    "co",
    "cl",
    "sec",
    "fig",
    "approx",
    "i.e",
    "e.g",
)

_SENT_END = re.compile(r"(?<=[.!?ം])[\s]+")
_NUMBERED_CLAUSE = re.compile(r"\n(?=\s*(?:\d{1,2}[.)]|\(\w{1,3}\)|[A-Z]{1,2}[.)])\s)")


def split_sentences(text: str) -> List[str]:
    """Split a block into sentence/clause units.

    Numbered or lettered clause headings start a new unit, which matters more
    for contracts than pure punctuation splitting.
    """
    if not text.strip():
        return []
    out: List[str] = []
    for block in _NUMBERED_CLAUSE.split(text):
        for para in block.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            pieces = _SENT_END.split(para.replace("\n", " "))
            buf = ""
            for piece in pieces:
                piece = piece.strip()
                if not piece:
                    continue
                candidate = f"{buf} {piece}".strip() if buf else piece
                last_word = re.split(r"[\s(]", candidate.rstrip(".").strip())[-1].lower()
                too_short = len(candidate.split()) < 3
                if last_word in _ABBREV or too_short:
                    buf = candidate
                    continue
                out.append(candidate)
                buf = ""
            if buf:
                out.append(buf)
    return [s for s in (x.strip() for x in out) if len(s) > 1]


def build_segments(pages: Iterable[Tuple[int, str]]) -> List[Segment]:
    """Turn (page_number, page_text) pairs into numbered segments."""
    segments: List[Segment] = []
    next_id = 1
    for page_no, page_text in pages:
        for sentence in split_sentences(page_text):
            if len(sentence) < 12:  # drop page furniture like "Page 2"
                continue
            segments.append(Segment(id=next_id, text=sentence, page=page_no))
            next_id += 1
    return segments


def segment_context(segments: List[Segment], index: int, window: int = 1) -> str:
    """Neighbouring segments on the same page, for clause context."""
    lo = max(0, index - window)
    hi = min(len(segments), index + window + 1)
    page = segments[index].page
    return " ".join(s.text for s in segments[lo:hi] if s.page == page)


def truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def normalise(text: str) -> str:
    """Lowercase, collapse whitespace: for keyword matching only."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def count_by(items: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def first_or_none(values: List[Optional[str]]) -> Optional[str]:
    for value in values:
        if value:
            return value
    return None
