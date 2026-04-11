from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app

_ANNOTATION = {
    "id": 1,
    "attempt_id": 1,
    "target_type": "evaluation",
    "sentiment": "down",
    "comment": "Feedback missed the point",
    "created_at": "2026-03-21T10:00:00+00:00",
    "question_text": "What is ATP?",
    "answer_text": "Energy currency.",
    "score": 5,
    "result_json": (
        '{"score": 5, "gaps": ["Missed synthesis"], "strengths": [],'
        ' "missing_points": [], "suggested_addition": null, "follow_up_question": "How?"}'
    ),
    "chunks": [],
}


@pytest.fixture()
def mock_session_store() -> MagicMock:
    store = MagicMock()
    store.load_annotation.return_value = _ANNOTATION
    return store


@pytest.fixture()
def client_with_github(tmp_path: Path, mock_session_store: MagicMock) -> Generator[TestClient]:
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore", return_value=mock_session_store),
        patch("learning_tool.api.routers.admin._GITHUB_CONFIGURED", True),
        patch("learning_tool.api.routers.admin.GITHUB_TOKEN", "fake-token"),
        patch("learning_tool.api.routers.admin.GITHUB_REPO", "owner/repo"),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


@pytest.fixture()
def client_no_github(tmp_path: Path, mock_session_store: MagicMock) -> Generator[TestClient]:
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore", return_value=mock_session_store),
        patch("learning_tool.api.routers.admin._GITHUB_CONFIGURED", False),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


def test_escalate_returns_503_when_github_not_configured(
    client_no_github: TestClient,
) -> None:
    response = client_no_github.post("/admin/annotations/1/escalate?context_name=ctx")
    assert response.status_code == 503


def test_escalate_returns_404_when_annotation_not_found(
    client_with_github: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotation.return_value = None
    response = client_with_github.post("/admin/annotations/99/escalate?context_name=ctx")
    assert response.status_code == 404


def test_escalate_calls_github_api_and_returns_fragment(
    client_with_github: TestClient,
) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        response = client_with_github.post("/admin/annotations/1/escalate?context_name=ctx")

    assert response.status_code == 200
    assert "github.com" in response.text
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["labels"] == ["feedback-quality"]
    assert "What is ATP?" in payload["body"]
    assert "Missed synthesis" in payload["body"]


def test_escalate_returns_502_on_github_api_error(
    client_with_github: TestClient,
) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        response = client_with_github.post("/admin/annotations/1/escalate?context_name=ctx")

    assert response.status_code == 502
