"""Tesseract OCR, used for images and for PDF pages with no embedded text.

Sizing is the single biggest factor in OCR accuracy on the kind of files
people actually upload. Tesseract wants roughly 300 DPI; a 376x531 screenshot
of an invoice puts the body text at about 8 pixels tall, and Tesseract returns
a few dozen characters of noise from a page that plainly holds a full table.
So small images are UPSCALED to a working size before recognition, large scans
are still downscaled to keep the demo fast, and each image is tried under more
than one page-segmentation mode with the best-scoring result kept.
"""
import io
import os
import logging
import shutil
from functools import lru_cache
from typing import List, Optional, Tuple

import config

logger = logging.getLogger(__name__)

# Page-segmentation modes worth trying, in order.
#   6 = assume a single uniform block of text. Best on invoices, bills and
#       tables, where the default mode often loses whole columns.
#   3 = fully automatic with page layout analysis. Better on multi-column
#       letters and notices.
#   4 = a single column of variable-size text. Good on receipts.
PSM_MODES = (6, 3, 4)


class OcrUnavailable(RuntimeError):
    """Tesseract is not installed or not reachable."""


@lru_cache(maxsize=1)
def ocr_status() -> Tuple[bool, str]:
    """(available, message). Cached: shutil.which on every page is waste."""
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False, "pytesseract is not installed (pip install pytesseract)."

    import pytesseract

    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    apply_tessdata_dir()
    cmd = pytesseract.pytesseract.tesseract_cmd or "tesseract"
    if shutil.which(cmd) is None:
        return (
            False,
            "Tesseract OCR was not found. Install it and, on Windows, set "
            "TESSERACT_CMD in .env to the full path of tesseract.exe.",
        )
    try:
        version = str(pytesseract.get_tesseract_version())
    except Exception as exc:  # pragma: no cover - depends on local install
        return False, "Tesseract was found but failed to run: %s" % exc
    return True, "Tesseract %s ready." % version


def apply_tessdata_dir() -> str:
    """Point Tesseract at a custom tessdata folder, if one is configured.

    TESSDATA_PREFIX is used rather than the --tessdata-dir flag: pytesseract
    splits its config string on whitespace, so a flag carrying a path with
    spaces (or quotes) reaches Tesseract mangled.
    """
    if not config.TESSDATA_DIR:
        return ""
    if not os.path.isdir(config.TESSDATA_DIR):
        logger.warning("TESSDATA_DIR does not exist: %s", config.TESSDATA_DIR)
        return ""
    os.environ["TESSDATA_PREFIX"] = config.TESSDATA_DIR
    return config.TESSDATA_DIR


@lru_cache(maxsize=1)
def available_languages() -> Tuple[str, ...]:
    ok, _ = ocr_status()
    if not ok:
        return ()
    import pytesseract

    try:
        apply_tessdata_dir()
        return tuple(pytesseract.get_languages(config=""))
    except Exception:  # pragma: no cover
        return ()


def resolve_langs() -> str:
    """Keep only requested languages whose traineddata is actually installed."""
    wanted = [p.strip() for p in config.OCR_LANGS.replace(",", "+").split("+") if p.strip()]
    installed = available_languages()
    if not installed:
        return "eng"
    keep = [w for w in wanted if w in installed]
    if not keep:
        keep = ["eng"] if "eng" in installed else [installed[0]]
    return "+".join(keep)


def _prepare(image):
    """Scale an image into Tesseract's comfortable range and clean it up.

    Both directions matter. Oversized scans are reduced because they cost time
    without adding accuracy. Undersized images - screenshots, WhatsApp photos,
    anything saved for the web - are enlarged, because below roughly 1,500
    pixels on the long edge the glyphs are too few pixels tall to recognise at
    all. Enlarging does not invent detail, but it does give the recogniser the
    pixel grid it expects, and in practice it is the difference between a few
    characters of noise and the whole page.
    """
    from PIL import Image, ImageOps, ImageFilter

    image = ImageOps.exif_transpose(image)
    # Palette and transparency modes confuse the greyscale conversion below,
    # so everything goes through RGB first.
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")

    longest = max(image.size)
    cap = config.OCR_MAX_IMAGE_PX
    floor = min(config.OCR_MIN_IMAGE_PX, cap)

    scale = 1.0
    if longest > cap:
        scale = cap / longest
    elif longest < floor:
        scale = floor / longest
        # Beyond about 4x, interpolation is inventing edges rather than
        # recovering them, and accuracy stops improving.
        scale = min(scale, config.OCR_MAX_UPSCALE)

    if scale != 1.0:
        new_size = (
            max(1, int(round(image.width * scale))),
            max(1, int(round(image.height * scale))),
        )
        # LANCZOS keeps thin strokes intact; BICUBIC smears them at these sizes.
        image = image.resize(new_size, Image.LANCZOS)

    # Greyscale helps Tesseract and halves the work.
    image = image.convert("L")
    # Stretch the histogram so faint scans and screenshots with grey-on-white
    # text reach full black. Cutting 1% off each end stops a single dark logo
    # or a shadow from setting the black point for the whole page.
    image = ImageOps.autocontrast(image, cutoff=1)
    if scale > 1.0:
        # Upscaling softens edges; one pass of unsharp masking puts the stroke
        # boundaries back without introducing the speckle that a plain sharpen
        # filter would.
        image = image.filter(ImageFilter.UnsharpMask(radius=1.4, percent=140, threshold=3))
    return image


def _score(text: str, confidence: Optional[float]) -> float:
    """How much usable document text a pass produced.

    Character count alone rewards noise, and mean confidence alone rewards a
    pass that found three clean words and missed the table. The product of the
    two, with letters and digits counted rather than punctuation, ranks the
    passes the way a person reading the output would.
    """
    useful = sum(1 for ch in text if ch.isalnum())
    if useful == 0:
        return 0.0
    # Words of two or more characters: OCR noise is mostly single stray glyphs.
    words = [w for w in text.split() if len(w) >= 2]
    base = useful + 4 * len(words)
    if confidence is None:
        return float(base)
    return base * max(confidence, 1.0) / 100.0


def _run_pass(image, lang: str, psm: int) -> Tuple[str, float]:
    """One OCR pass. Returns (text, score)."""
    import pytesseract

    cfg = "--oem 3 --psm %d" % psm
    try:
        data = pytesseract.image_to_data(
            image, lang=lang, config=cfg, output_type=pytesseract.Output.DICT
        )
    except Exception:
        # image_to_data can fail on some builds where image_to_string works.
        text = pytesseract.image_to_string(image, lang=lang, config=cfg)
        return text, _score(text, None)

    words: List[str] = []
    confidences: List[float] = []
    last_line = None
    for i, word in enumerate(data.get("text", [])):
        word = (word or "").strip()
        try:
            conf = float(data["conf"][i])
        except (KeyError, IndexError, TypeError, ValueError):
            conf = -1.0
        if not word or conf < 0:
            continue
        line = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        if last_line is not None and line != last_line:
            words.append("\n")
        last_line = line
        words.append(word)
        confidences.append(conf)

    text = " ".join(words).replace(" \n ", "\n").replace(" \n", "\n").replace("\n ", "\n")
    mean_conf = sum(confidences) / len(confidences) if confidences else None
    return text, _score(text, mean_conf)


def _language_candidates() -> List[str]:
    """Language sets to try, cheapest and most likely first.

    Handing Tesseract "eng+mal" for an English invoice is not free: the
    Malayalam model competes for every glyph and wins on logos and stylised
    headings, which is how "STUDIO SHODWE" acquires a Malayalam character.
    English alone is tried first and the multilingual set only when English
    alone did badly, so a Malayalam document still reads correctly while an
    English one stops being contaminated.
    """
    resolved = resolve_langs()
    parts = resolved.split("+")
    if len(parts) <= 1:
        return [resolved]
    if "eng" in parts:
        return ["eng", resolved]
    return [resolved]


def _best_pass(prepared, lang: str) -> Tuple[str, float]:
    best_text, best_score = "", 0.0
    for psm in PSM_MODES[: max(1, config.OCR_PASSES)]:
        try:
            text, score = _run_pass(prepared, lang, psm)
        except Exception as exc:  # pragma: no cover - local tesseract failures
            logger.warning("OCR pass lang=%s psm=%s failed: %s", lang, psm, exc)
            continue
        logger.debug("OCR lang=%s psm=%s score=%.1f chars=%d", lang, psm, score, len(text))
        if score > best_score:
            best_text, best_score = text, score
        # A clearly good pass makes the remaining ones a waste of the demo
        # laptop's time.
        if best_score >= config.OCR_GOOD_ENOUGH_SCORE:
            break
    return best_text, best_score


def ocr_image(image, lang: Optional[str] = None) -> str:
    """Recognise a PIL image, trying each segmentation mode and keeping the best.

    The modes disagree most on exactly the documents this product targets:
    invoices and bills, where the default layout analysis frequently drops a
    whole column of amounts that the single-block mode reads cleanly.
    """
    import pytesseract  # noqa: F401

    apply_tessdata_dir()
    prepared = _prepare(image)
    candidates = [lang] if lang else _language_candidates()

    best_text, best_score = "", 0.0
    for index, candidate in enumerate(candidates):
        text, score = _best_pass(prepared, candidate)
        # Later candidates add scripts to the recogniser. They have to be
        # clearly better, not merely equal, to displace a simpler one: a tie
        # means the extra script contributed nothing but did get to overwrite
        # the odd stylised heading with a character from the wrong alphabet.
        threshold = best_score * config.OCR_LANG_SWITCH_MARGIN if index else best_score
        if score > threshold:
            best_text, best_score = text, score
        if best_score >= config.OCR_GOOD_ENOUGH_SCORE:
            break

    # A blank page is a result, not a failure: return nothing and let the
    # caller say "OCR read no text", which is the accurate message.
    return best_text


def ocr_image_bytes(data: bytes) -> str:
    ok, message = ocr_status()
    if not ok:
        raise OcrUnavailable(message)
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            return ocr_image(img)
    except UnidentifiedImageError as exc:
        raise ValueError("The uploaded file is not a readable image.") from exc
    except OcrUnavailable:
        raise
    except Exception as exc:  # pragma: no cover - local tesseract failures
        raise OcrUnavailable("OCR failed: %s" % exc) from exc
