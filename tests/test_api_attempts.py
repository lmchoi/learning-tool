import json
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


def _make_client(
    mock_session_store: MagicMock, store_exists: bool = True
) -> Generator[tuple[TestClient, MagicMock]]:
    context_path = MagicMock()
    context_path.exists.return_value = store_exists
    store_dir = MagicMock()
    store_dir.__truediv__ = MagicMock(return_value=context_path)
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.Retriever"),
        patch("api.main.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        app.state.store_dir = store_dir
        yield c, mock_session_store


@pytest.fixture()
def client_ok() -> Generator[tuple[TestClient, MagicMock]]:
    mock_store = MagicMock()
    mock_store.record.return_value = 42
    yield from _make_client(mock_store)


@pytest.fixture()
def client_no_context() -> Generator[tuple[TestClient, MagicMock]]:
    mock_store = MagicMock()
    yield from _make_client(mock_store, store_exists=False)


_VALID_PAYLOAD = {
    "context": "biology",
    "session_id": "sess-abc",
    "question_id": "q-123",
    "question": "What is a cell?",
    "answer": "The smallest unit of life.",
    "evaluation": {"score": 7, "strengths": ["correct"], "gaps": []},
    "score": 7,
}


def test_post_attempt_returns_201(client_ok: tuple[TestClient, MagicMock]) -> None:
    client, _ = client_ok
    response = client.post("/api/attempts", json=_VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["attempt_id"] == 42


def test_post_attempt_records_to_session_store(client_ok: tuple[TestClient, MagicMock]) -> None:
    client, mock_store = client_ok
    client.post("/api/attempts", json=_VALID_PAYLOAD)

    mock_store.record.assert_called_once()
    call_args = mock_store.record.call_args
    args, kwargs = call_args
    assert args[0] == "sess-abc"
    assert args[1] == "What is a cell?"
    assert args[2] == "The smallest unit of life."
    assert args[3] == 7
    assert args[4] == "q-123"
    assert args[5] == json.dumps({"score": 7, "strengths": ["correct"], "gaps": []})


def test_post_attempt_threads_focus_area(client_ok: tuple[TestClient, MagicMock]) -> None:
    client, mock_store = client_ok
    payload = {**_VALID_PAYLOAD, "focus_area": "cell biology"}
    client.post("/api/attempts", json=payload)

    call_args = mock_store.record.call_args
    # focus_area is passed as a keyword argument
    assert call_args.kwargs["focus_area"] == "cell biology"


def test_post_attempt_focus_area_defaults_to_none(client_ok: tuple[TestClient, MagicMock]) -> None:
    client, mock_store = client_ok
    client.post("/api/attempts", json=_VALID_PAYLOAD)

    call_args = mock_store.record.call_args
    # focus_area not in payload → passes None
    assert call_args.kwargs["focus_area"] is None


def test_post_attempt_400_invalid_context_name(client_ok: tuple[TestClient, MagicMock]) -> None:
    client, _ = client_ok
    payload = {**_VALID_PAYLOAD, "context": "../evil"}
    response = client.post("/api/attempts", json=payload)

    assert response.status_code == 400


def test_post_attempt_404_context_not_found(
    client_no_context: tuple[TestClient, MagicMock],
) -> None:
    client, _ = client_no_context
    response = client.post("/api/attempts", json=_VALID_PAYLOAD)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
