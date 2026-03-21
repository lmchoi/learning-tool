from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def mock_retriever() -> Generator[MagicMock]:
    with patch("api.main.Retriever") as mock_cls:
        yield mock_cls.return_value


@pytest.fixture()
def mock_session_store() -> MagicMock:
    store = MagicMock()
    store.start_session.return_value = "test-session-id"
    return store


@pytest.fixture()
def client(
    tmp_path: Path, mock_retriever: MagicMock, mock_session_store: MagicMock
) -> Generator[TestClient]:
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


def test_post_annotate_valid_up(client: TestClient, mock_session_store: MagicMock) -> None:
    response = client.post(
        "/annotate",
        data={"attempt_id": "1", "context_name": "ctx", "sentiment": "up"},
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    mock_session_store.record_annotation.assert_called_once_with(1, "question", "up", None)


def test_post_annotate_valid_down_with_comment(client: TestClient) -> None:
    response = client.post(
        "/annotate",
        data={
            "attempt_id": "1",
            "context_name": "ctx",
            "sentiment": "down",
            "comment": "Confusing question",
        },
    )

    assert response.status_code == 200


def test_post_annotate_invalid_sentiment(client: TestClient) -> None:
    response = client.post(
        "/annotate",
        data={"attempt_id": "1", "context_name": "ctx", "sentiment": "meh"},
    )

    assert response.status_code == 422


def test_post_annotate_response_shows_sentiment(client: TestClient) -> None:
    response = client.post(
        "/annotate",
        data={"attempt_id": "1", "context_name": "ctx", "sentiment": "up"},
    )

    assert "Saved" in response.text
