"""Offline speech synthesis via eSpeak NG.

The browser's own voices are used first. Windows ships no Malayalam voice, so
without a local fallback Malayalam audio silently reads in an English voice.
eSpeak NG covers Malayalam, runs entirely offline and is a few megabytes, which
keeps the privacy promise intact: no text is sent anywhere.

The engine is optional. When it is absent every function here reports that
plainly rather than failing the request.
"""
import logging
import os
import shutil
import subprocess
from functools import lru_cache
from typing import List, Optional, Tuple

import config

logger = logging.getLogger(__name__)

# eSpeak NG voice names per app language.
VOICE_BY_LANGUAGE = {
    "en": "en-gb",
    "ml": "ml",
}

MAX_TTS_CHARS = 1200
TTS_TIMEOUT_SECONDS = 30

_WINDOWS_DEFAULTS = (
    r"C:\Program Files\eSpeak NG\espeak-ng.exe",
    r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
)


class TtsUnavailable(RuntimeError):
    """eSpeak NG is not installed or could not run."""


@lru_cache(maxsize=1)
def find_espeak() -> Optional[str]:
    """Locate espeak-ng: explicit config, then PATH, then the usual install dirs."""
    configured = getattr(config, "ESPEAK_CMD", "")
    if configured:
        if os.path.isfile(configured):
            return configured
        found = shutil.which(configured)
        if found:
            return found
        logger.warning("ESPEAK_CMD is set but not usable: %s", configured)

    for name in ("espeak-ng", "espeak"):
        found = shutil.which(name)
        if found:
            return found

    for candidate in _WINDOWS_DEFAULTS:
        if os.path.isfile(candidate):
            return candidate
    return None


@lru_cache(maxsize=1)
def tts_status() -> Tuple[bool, str, List[str]]:
    """(available, message, languages)."""
    binary = find_espeak()
    if not binary:
        return (
            False,
            "eSpeak NG is not installed, so the server cannot speak languages your "
            "browser has no voice for. Install it with: "
            "winget install eSpeak-NG.eSpeak-NG",
            [],
        )
    try:
        result = subprocess.run(
            [binary, "--voices"],
            capture_output=True,
            text=True,
            timeout=TTS_TIMEOUT_SECONDS,
            check=True,
        )
    except Exception as exc:  # pragma: no cover - depends on local install
        return False, "eSpeak NG was found but failed to run: %s" % exc, []

    codes = set()
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            codes.add(parts[1].split("-")[0])

    available = sorted(code for code in VOICE_BY_LANGUAGE.values() if code.split("-")[0] in codes)
    return True, "eSpeak NG ready at %s." % binary, available


def language_supported(language: str) -> bool:
    ok, _message, available = tts_status()
    if not ok:
        return False
    wanted = VOICE_BY_LANGUAGE.get(language, "en-gb")
    return any(v.split("-")[0] == wanted.split("-")[0] for v in available)


def synthesize(text: str, language: str = "en", speed: int = 150) -> bytes:
    """Render text to WAV bytes. Raises TtsUnavailable when the engine is missing."""
    binary = find_espeak()
    if not binary:
        raise TtsUnavailable(tts_status()[1])

    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Nothing to speak.")
    if len(cleaned) > MAX_TTS_CHARS:
        cleaned = cleaned[:MAX_TTS_CHARS]

    voice = VOICE_BY_LANGUAGE.get(language, "en-gb")
    # Validate voice name contains only safe characters (defence in depth).
    if not all(c.isalnum() or c in "-_" for c in voice):
        raise ValueError("Invalid voice identifier.")
    # Argument list, never a shell string: the text is document-derived and must
    # not be interpreted by a shell.
    command = [
        binary,
        "-v",
        voice,
        "-s",
        str(max(80, min(speed, 260))),
        "--stdout",
        "--",  # everything after this is data, not options
        cleaned,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=TTS_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise TtsUnavailable("Speech synthesis timed out.") from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover
        detail = (exc.stderr or b"").decode("utf-8", "replace")[:200]
        raise TtsUnavailable("eSpeak NG failed: %s" % detail) from exc

    if not result.stdout:
        raise TtsUnavailable("eSpeak NG produced no audio.")
    return result.stdout
