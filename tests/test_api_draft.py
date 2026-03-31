from collections.abc import Generator
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.context_import.draft_store import DraftStore


def _make_client(store_dir: Path) -> Generator[TestClient]:
    with ExitStack() as stack:
        stack.enter_context(patch("api.main.SentenceTransformerEmbedder"))
        stack.enter_context(patch("api.main.AsyncAnthropic"))
        stack.enter_context(patch("api.main.genai"))
        stack.enter_context(patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}))
        c = TestClient(app)
        c.app.state.store_dir = store_dir  # type: ignore[attr-defined]
        c.app.state.draft_store = DraftStore(store_dir)  # type: ignore[attr-defined]
        yield c


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    yield from _make_client(tmp_path)


def test_post_draft_creates_draft_and_returns_url(client: TestClient) -> None:
    payload = {"goal": "Test goal", "focus_areas": [{"name": "Area 1", "questions": ["Q1", "Q2"]}]}
    response = client.post("/api/contexts/test-context/draft", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "draft_id" in data
    assert "review_url" in data
    assert data["review_url"] == f"/ui/test-context/review/{data['draft_id']}"


def test_get_review_renders_template(client: TestClient) -> None:
    # First create a draft
    payload = {"goal": "Test goal", "focus_areas": [{"name": "Area 1", "questions": ["Q1", "Q2"]}]}
    draft_res = client.post("/api/contexts/test-context/draft", json=payload)
    draft_id = draft_res.json()["draft_id"]

    # Then get the review page
    response = client.get(f"/ui/test-context/review/{draft_id}")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Test goal" in response.text
    assert "Area 1" in response.text
    assert "Q1" in response.text


def test_get_review_nonexistent_returns_404(client: TestClient) -> None:
    response = client.get("/ui/test-context/review/nonexistent")
    assert response.status_code == 404


def test_get_review_invalid_id_returns_404(client: TestClient) -> None:
    # Tests that IDs failing the whitelist also 404 cleanly via API
    response = client.get("/ui/test-context/review/../etc")
    assert response.status_code == 404


def test_get_review_wrong_context_returns_404(client: TestClient) -> None:
    payload = {"goal": "g", "focus_areas": []}
    draft_res = client.post("/api/contexts/test-context/draft", json=payload)
    draft_id = draft_res.json()["draft_id"]

    # Try to load the draft for a different context
    response = client.get(f"/ui/other-context/review/{draft_id}")
    assert response.status_code == 404


def test_post_draft_invalid_context_name_returns_422(client: TestClient) -> None:
    payload = {"goal": "g", "focus_areas": []}
    response = client.post("/api/contexts/invalid name/draft", json=payload)
    assert response.status_code == 422
