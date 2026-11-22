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
_status_cache: Optional[Tuple[float, OllamaStatus]] = None


class OllamaError(RuntimeError):
    """Ollama was reachable but the request failed."""


class OllamaUnavailable(OllamaError):
    """Ollama is not running, or the configured model is not installed."""


def _setup_hint() -> str:
    return (
        "Start Ollama, then install the model:\n"
        "  ollama serve\n"
        "  ollama pull %s\n"
        "Or set OLLAMA_MODEL in .env to a model you already have." % config.OLLAMA_MODEL
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


def check_status(force: bool = False) -> OllamaStatus:
    global _status_cache
    now = time.monotonic()
    if not force and _status_cache and (now - _status_cache[0]) < _STATUS_TTL_SECONDS:
        return _status_cache[1]

    status = OllamaStatus(
        reachable=False,
        model=config.OLLAMA_MODEL,
        model_available=False,
        base_url=config.OLLAMA_BASE_URL,
    )
    try:
        models = list_models()
    except httpx.HTTPError as exc:
        status.message = (
            "Ollama is not reachable at %s (%s). %s"
            % (config.OLLAMA_BASE_URL, type(exc).__name__, _setup_hint())
        )
        _status_cache = (now, status)
        return status
    except Exception as exc:  # pragma: no cover - unexpected payload
        status.message = "Could not read the Ollama model list: %s" % exc
        _status_cache = (now, status)
        return status

    status.reachable = True
    status.models_installed = models
    wanted = config.OLLAMA_MODEL.strip().lower()
    exact = any(m.strip().lower() == wanted for m in models)
    loose = any(_normalise_name(m) == _normalise_name(wanted) for m in models)
    status.model_available = exact or loose
    if status.model_available:
        status.message = "Ollama is running with model %s." % config.OLLAMA_MODEL
    else:
        installed = ", ".join(models) if models else "none"
        status.message = (
            'Ollama is running but model "%s" is not installed (installed: %s). %s'
            % (config.OLLAMA_MODEL, installed, _setup_hint())
        )
    _status_cache = (now, status)
    return status


def is_ready() -> bool:
    status = check_status()
    return status.reachable and status.model_available


def generate(
    prompt: str,
    system: str = "",
    json_mode: bool = False,
    temperature: float = 0.1,
    num_predict: int = 900,
    timeout: Optional[int] = None,
) -> str:
    """One /api/generate call. Raises OllamaUnavailable when not usable."""
    status = check_status()
    if not status.reachable or not status.model_available:
        raise OllamaUnavailable(status.message)

    payload: Dict = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
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
        config.OLLAMA_MODEL,
        json_mode,
        time.monotonic() - started,
    )
    return (data.get("response") or "").strip()


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
    raise OllamaError(
        "The model did not return valid JSON. Try a different OLLAMA_MODEL. (%s)" % last_error
    )
