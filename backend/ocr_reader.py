"""Tesseract OCR, used only when embedded PDF text is missing."""
import io
import logging
import shutil
from functools import lru_cache
from typing import List, Tuple

import config

logger = logging.getLogger(__name__)


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


@lru_cache(maxsize=1)
def available_languages() -> Tuple[str, ...]:
    ok, _ = ocr_status()
    if not ok:
        return ()
    import pytesseract

    try:
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
    """Downscale oversized scans. Large images cost OCR time, not accuracy."""
    from PIL import Image, ImageOps

    image = ImageOps.exif_transpose(image)
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    longest = max(image.size)
    cap = config.OCR_MAX_IMAGE_PX
    if longest > cap:
        scale = cap / longest
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        image = image.resize(new_size, Image.LANCZOS)
    # Greyscale helps Tesseract and halves the work.
    return image.convert("L")


def ocr_image_bytes(data: bytes) -> str:
    ok, message = ocr_status()
    if not ok:
        raise OcrUnavailable(message)
    import pytesseract
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as img:
            prepared = _prepare(img)
    except UnidentifiedImageError as exc:
        raise ValueError("The uploaded file is not a readable image.") from exc

    try:
        return pytesseract.image_to_string(prepared, lang=resolve_langs())
    except Exception as exc:  # pragma: no cover - local tesseract failures
        raise OcrUnavailable("OCR failed: %s" % exc) from exc
