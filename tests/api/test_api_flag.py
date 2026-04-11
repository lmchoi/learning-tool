from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app

_ANNOTATION = {
    "id": 1,
    "attempt_id": 1,
    "target_type": "evaluation",
    "sentiment": "down",
    "comment": None,
    "created_at": "2026-03-22T10:00:00+00:00",
    "question_text": "What is ATP?",
    "answer_text": "Energy currency.",
    "score": 5,
    "result_json": None,
    "chunks": [],
    "flagged_at": None,
}


@pytest.fixture()
def mock_session_store() -> MagicMock:
    store = MagicMock()
    store.load_annotation.return_value = _ANNOTATION
    return store


@pytest.fixture()
def client(tmp_path: Path, mock_session_store: MagicMock) -> Generator[TestClient]:
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


def test_flag_returns_404_when_annotation_not_found(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotation.return_value = None
    response = client.post("/admin/annotations/99/flag?context_name=ctx")
    assert response.status_code == 404


def test_flag_calls_flag_annotation_and_returns_fragment(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    response = client.post("/admin/annotations/1/flag?context_name=ctx")
    assert response.status_code == 200
    mock_session_store.flag_annotation.assert_called_once_with(1)
    assert "Flagged for review" in response.text
