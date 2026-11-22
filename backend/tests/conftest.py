"""Shared fixtures. Adds the backend folder to sys.path so the modules import
the same way they do when uvicorn runs from inside backend/."""
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DEMO_DIR = PROJECT_ROOT / "demo"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _ensure_demo_docs() -> None:
    if (DEMO_DIR / "demo_rental_agreement.pdf").exists():
        return
    sys.path.insert(0, str(DEMO_DIR))
    import make_demo_docs

    make_demo_docs.main()


@pytest.fixture(scope="session", autouse=True)
def demo_docs():
    _ensure_demo_docs()
    return DEMO_DIR


@pytest.fixture(scope="session")
def rental_pdf_bytes(demo_docs):
    return (demo_docs / "demo_rental_agreement.pdf").read_bytes()


@pytest.fixture(scope="session")
def loan_pdf_bytes(demo_docs):
    return (demo_docs / "demo_loan_agreement.pdf").read_bytes()


@pytest.fixture(scope="session")
def bill_pdf_bytes(demo_docs):
    return (demo_docs / "demo_hospital_bill.pdf").read_bytes()


@pytest.fixture(scope="session")
def notice_pdf_bytes(demo_docs):
    return (demo_docs / "demo_government_notice.pdf").read_bytes()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app)


@pytest.fixture
def ollama_down(monkeypatch):
    """Force every Ollama call to fail the way an unreachable server does."""
    import ollama_service

    status = ollama_service.OllamaStatus(
        reachable=False,
        model="test-model",
        model_available=False,
        base_url="http://localhost:11434",
        message="Ollama is not reachable (test).",
    )
    monkeypatch.setattr(
        ollama_service,
        "check_status",
        lambda force=False, model=None: status,
    )

    def refuse(*_args, **_kwargs):
        raise ollama_service.OllamaUnavailable(status.message)

    monkeypatch.setattr(ollama_service, "generate", refuse)
    monkeypatch.setattr(ollama_service, "generate_json", refuse)
    return status
