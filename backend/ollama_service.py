"""Thin client for the local Ollama HTTP API. The only LLM provider here."""
import json
import logging
import time
from typing import Dict, List, Optional, Tuple

import httpx

import config
from schemas import OllamaStatus

logger = logging.getLogger(__name__)

# Status is cached briefly so one analysis does not probe Ollama repeatedly.
_STATUS_TTL_SECONDS = 10
# Keyed by model name: English and Malayalam may use different models.
_status_cache: Dict[str, Tuple[float, OllamaStatus]] = {}


class OllamaError(RuntimeError):
    """Ollama was reachable but the request failed."""


class OllamaUnavailable(OllamaError):
    """Ollama is not running, or the configured model is not installed."""


def _setup_hint(model: str) -> str:
    return (
        "Start Ollama, then install the model:\n"
        "  ollama serve\n"
        "  ollama pull %s\n"
        "Or set OLLAMA_MODEL in .env to a model you already have." % model
    )


def _normalise_name(name: str) -> str:
    """Ollama reports 'qwen2.5:3b'; a bare 'qwen2.5' should still match."""
    return name.split(":")[0].strip().lower()


def list_models() -> List[str]:
    with httpx.Client(timeout=5.0) as client:
        response = client.get(config.OLLAMA_BASE_URL + "/api/tags")
        response.raise_for_status()
        payload = response.json()
    return [m.get("name", "") for m in payload.get("models", []) if m.get("name")]


def check_status(force: bool = False, model: Optional[str] = None) -> OllamaStatus:
    model = (model or config.OLLAMA_MODEL).strip()
    now = time.monotonic()
    cached = _status_cache.get(model)
    if not force and cached and (now - cached[0]) < _STATUS_TTL_SECONDS:
        return cached[1]

    status = OllamaStatus(
        reachable=False,
        model=model,
        model_available=False,
        base_url=config.OLLAMA_BASE_URL,
    )
    try:
        models = list_models()
    except httpx.HTTPError as exc:
        status.message = (
            "Ollama is not reachable at %s (%s). %s"
            % (config.OLLAMA_BASE_URL, type(exc).__name__, _setup_hint(model))
        )
        _status_cache[model] = (now, status)
        return status
    except Exception as exc:  # pragma: no cover - unexpected payload
        status.message = "Could not read the Ollama model list: %s" % exc
        _status_cache[model] = (now, status)
        return status

    status.reachable = True
    status.models_installed = models
    wanted = model.lower()
    exact = any(m.strip().lower() == wanted for m in models)
    loose = any(_normalise_name(m) == _normalise_name(wanted) for m in models)
    status.model_available = exact or loose
    if status.model_available:
        status.message = "Ollama is running with model %s." % model
    else:
        installed = ", ".join(models) if models else "none"
        status.message = (
            'Ollama is running but model "%s" is not installed (installed: %s). %s'
            % (model, installed, _setup_hint(model))
        )
    _status_cache[model] = (now, status)
    return status


def is_ready(model: Optional[str] = None) -> bool:
    status = check_status(model=model)
    return status.reachable and status.model_available


def generate(
    prompt: str,
    system: str = "",
    json_mode: bool = False,
    temperature: float = 0.1,
    num_predict: int = 900,
    timeout: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """One /api/generate call. Raises OllamaUnavailable when not usable."""
    model = (model or config.OLLAMA_MODEL).strip()
    status = check_status(model=model)
    if not status.reachable or not status.model_available:
        raise OllamaUnavailable(status.message)

    payload: Dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        # Keep the model resident between requests. Without this Ollama unloads
        # it after a few idle minutes and the next upload pays the full cold
        # load again, which on a laptop can exceed the request timeout.
        "keep_alive": config.OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            # Keep the context modest: prompts here are clause-sized by design.
            "num_ctx": 4096,
        },
    }
    if system:
        payload["system"] = system
    if json_mode:
        payload["format"] = "json"

    started = time.monotonic()
    try:
        with httpx.Client(timeout=timeout or config.OLLAMA_TIMEOUT) as client:
            response = client.post(config.OLLAMA_BASE_URL + "/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise OllamaError(
            "The local model did not answer within %ss. Try a smaller model or raise "
            "OLLAMA_TIMEOUT in .env." % (timeout or config.OLLAMA_TIMEOUT)
        ) from exc
    except httpx.HTTPError as exc:
        raise OllamaUnavailable("Ollama request failed: %s" % exc) from exc

    logger.info(
        "ollama generate ok model=%s json=%s %.1fs",
        model,
        json_mode,
        time.monotonic() - started,
    )
    return (data.get("response") or "").strip()


def warm_up(model: Optional[str] = None) -> bool:
    """Load the model into memory before the first real request.

    Loading a 2 GB model from a cold disk can take longer than the request
    timeout, which is what makes a first upload look broken. Called in the
    background at startup, so it never blocks the server coming up.
    """
    model = (model or config.OLLAMA_MODEL).strip()
    status = check_status(force=True, model=model)
    if not (status.reachable and status.model_available):
        logger.info("Ollama warm-up skipped: %s", status.message)
        return False
    try:
        with httpx.Client(timeout=config.OLLAMA_WARMUP_TIMEOUT) as client:
            client.post(
                config.OLLAMA_BASE_URL + "/api/generate",
                json={
                    "model": model,
                    # An empty prompt loads the model without generating.
                    "prompt": "",
                    "stream": False,
                    "keep_alive": config.OLLAMA_KEEP_ALIVE,
                },
            ).raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Ollama warm-up failed: %s", exc)
        return False
    logger.info("Ollama model %s loaded and ready.", model)
    return True


class OllamaBadJson(OllamaError):
    """The model answered, but the JSON could not be parsed.

    Carries the raw reply so the caller can salvage whatever is complete. A
    reply truncated by the token limit is the common case, and regenerating it
    just truncates again at the same place, so salvage beats retry.
    """

    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


def salvage_json_objects(raw: str) -> List[Dict]:
    """Pull every complete {...} object out of a truncated JSON reply.

    Brace counting, skipping braces inside strings. An object that was cut off
    mid-way is simply dropped.

    The objects we want are nested inside {"explanations": [...]}, and that
    outer object is exactly the one truncation leaves unclosed, so every depth
    is tracked rather than only the top level.
    """
    found: List[Tuple[int, Dict]] = []
    starts: List[int] = []
    in_string = False
    escaped = False
    for index, char in enumerate(raw):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            starts.append(index)
        elif char == "}" and starts:
            start = starts.pop()
            try:
                parsed = json.loads(raw[start : index + 1])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                found.append((start, parsed))
    # A closing brace is seen innermost-first, so sort by opening position to
    # hand the caller the objects in the order the model wrote them.
    found.sort(key=lambda row: row[0])
    return [obj for _start, obj in found]


def _extract_json_block(raw: str) -> str:
    """Pull the outermost JSON object out of a chatty reply."""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise OllamaError("The model reply contained no JSON object.")
    return raw[start : end + 1]


def generate_json(
    prompt: str,
    system: str = "",
    retries: int = 1,
    num_predict: int = 900,
    timeout: Optional[int] = None,
    model: Optional[str] = None,
) -> Dict:
    """Ask for JSON and parse it. One retry, then give up honestly."""
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        raw = generate(
            prompt,
            system=system,
            json_mode=True,
            temperature=0.1 if attempt == 0 else 0.0,
            num_predict=num_predict,
            timeout=timeout,
            model=model,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            last_error = exc
            try:
                return json.loads(_extract_json_block(raw))
            except Exception as inner:
                last_error = inner
                logger.warning("Ollama JSON parse failed (attempt %s): %s", attempt + 1, inner)
    raise OllamaBadJson(
        "The model did not return valid JSON. Try a different OLLAMA_MODEL. (%s)"
        % last_error,
        raw=raw,
    )
