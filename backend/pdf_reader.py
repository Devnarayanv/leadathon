"""PDF text extraction with a per-page OCR fallback for scanned pages."""
import logging
from typing import Dict, List, Tuple

import pymupdf as fitz  # PyMuPDF 1.24+ exposes the package as pymupdf

import config
from ocr_reader import OcrUnavailable, ocr_image_bytes, ocr_status
from schemas import PageText
from utils import clean_text

logger = logging.getLogger(__name__)

# Below this many characters a page is treated as scanned / image-only.
MIN_CHARS_PER_PAGE = 60


class UnreadableDocument(ValueError):
    """The file could not be opened or read."""


def _new_info() -> Dict:
    return {
        "ocr_used": False,
        "ocr_pages": [],
        "ocr_available": True,
        "ocr_message": "",
        "warnings": [],
        "truncated": False,
        "total_pages": 0,
    }


def _needs_ocr(text: str) -> bool:
    return len(text.strip()) < MIN_CHARS_PER_PAGE


def extract_pdf(data: bytes) -> Tuple[List[PageText], Dict]:
    """Return per-page text plus an info dict.

    Embedded text first. Only pages that come back (near) empty are rendered
    and sent to OCR, and that is capped by OCR_MAX_PAGES.
    """
    info = _new_info()
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UnreadableDocument(
            "This PDF could not be opened. It may be corrupted or not a real PDF."
        ) from exc

    with doc:
        if doc.needs_pass:
            raise UnreadableDocument(
                "This PDF is password protected. Remove the password and upload again."
            )

        info["total_pages"] = doc.page_count
        if doc.page_count == 0:
            raise UnreadableDocument("This PDF has no pages.")

        limit = min(doc.page_count, config.MAX_PAGES)
        if doc.page_count > limit:
            info["truncated"] = True
            info["warnings"].append(
                "Only the first %d of %d pages were analysed." % (limit, doc.page_count)
            )

        pages: List[PageText] = []
        ocr_candidates: List[int] = []
        for index in range(limit):
            text = clean_text(doc.load_page(index).get_text("text"))
            if _needs_ocr(text):
                ocr_candidates.append(index)
                pages.append(PageText(page=index + 1, text=text, source="empty"))
            else:
                pages.append(PageText(page=index + 1, text=text, source="pdf_text"))

        if ocr_candidates:
            _ocr_missing_pages(doc, pages, ocr_candidates, info)

    if not any(p.text.strip() for p in pages):
        info["warnings"].append(
            "No text could be read from this document. If it is a scan, install "
            "Tesseract OCR and try again."
        )
    return pages, info


def _ocr_missing_pages(doc, pages: List[PageText], candidates: List[int], info: Dict) -> None:
    ok, message = ocr_status()
    info["ocr_available"] = ok
    info["ocr_message"] = message
    if not ok:
        info["warnings"].append(
            "%d page(s) hold no selectable text and OCR is unavailable. %s"
            % (len(candidates), message)
        )
        return

    budget = candidates[: config.OCR_MAX_PAGES]
    if len(candidates) > len(budget):
        info["warnings"].append(
            "OCR ran on %d of %d image-only pages (OCR_MAX_PAGES=%d)."
            % (len(budget), len(candidates), config.OCR_MAX_PAGES)
        )
    zoom = config.OCR_DPI / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for index in budget:
        try:
            pixmap = doc.load_page(index).get_pixmap(matrix=matrix)
            text = clean_text(ocr_image_bytes(pixmap.tobytes("png")))
        except OcrUnavailable as exc:
            info["ocr_available"] = False
            info["ocr_message"] = str(exc)
            info["warnings"].append(str(exc))
            return
        except Exception as exc:  # pragma: no cover - local render/OCR failures
            logger.warning("OCR failed on page %s: %s", index + 1, exc)
            info["warnings"].append("OCR failed on page %d." % (index + 1))
            continue
        if text.strip():
            pages[index] = PageText(page=index + 1, text=text, source="ocr")
            info["ocr_used"] = True
            info["ocr_pages"].append(index + 1)


def extract_image(data: bytes) -> Tuple[List[PageText], Dict]:
    """Single-page extraction for an uploaded photo or scan."""
    info = _new_info()
    info["total_pages"] = 1
    ok, message = ocr_status()
    info["ocr_available"] = ok
    info["ocr_message"] = message
    if not ok:
        info["warnings"].append("Image uploads need OCR, which is unavailable. " + message)
        return [PageText(page=1, text="", source="empty")], info

    text = clean_text(ocr_image_bytes(data))
    if not text.strip():
        info["warnings"].append(
            "OCR read no text from this image. Try a sharper, well-lit photo."
        )
        return [PageText(page=1, text="", source="empty")], info

    info["ocr_used"] = True
    info["ocr_pages"] = [1]
    return [PageText(page=1, text=text, source="ocr")], info
