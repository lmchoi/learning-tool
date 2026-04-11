import json
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.session.models import QuestionAttempt, SessionRecord


@pytest.fixture()
def client_and_store() -> Generator[tuple[TestClient, MagicMock]]:
    mock_session_store = MagicMock()
    app.state.session_stores = {}
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c, mock_session_store


def _attempt(
    question: str = "What is X?",
    answer: str = "It is Y.",
    score: int = 7,
    result: dict[str, object] | None = None,
) -> QuestionAttempt:
    return QuestionAttempt(
        session_id="abc123",
        question_text=question,
        answer_text=answer,
        score=score,
        timestamp="2026-03-25T10:00:00+00:00",
        result_json=json.dumps(result) if result else None,
    )


def _session(attempts: list[QuestionAttempt]) -> SessionRecord:
    return SessionRecord(
        session_id="abc123",
        context="my-context",
        started_at="2026-03-25T09:00:00+00:00",
        attempts=attempts,
    )


def test_get_session_results_returns_200(
    client_and_store: tuple[TestClient, MagicMock],
) -> None:
    client, store = client_and_store
    store.load_session.return_value = _session([_attempt()])

    response = client.get("/ui/my-context/sessions/abc123")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_session_results_shows_attempts(
    client_and_store: tuple[TestClient, MagicMock],
) -> None:
    client, store = client_and_store
    store.load_session.return_value = _session(
        [_attempt(question="What is async?", answer="Non-blocking.", score=8)]
    )

    response = client.get("/ui/my-context/sessions/abc123")

    assert "What is async?" in response.text
    assert "Non-blocking." in response.text
    assert "8/10" in response.text


def test_get_session_results_unknown_session_returns_404(
    client_and_store: tuple[TestClient, MagicMock],
) -> None:
    client, store = client_and_store
    store.load_session.return_value = None

    response = client.get("/ui/my-context/sessions/unknown-id")

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "not found" in response.text.lower()


def test_get_session_results_shows_evaluation_breakdown(
    client_and_store: tuple[TestClient, MagicMock],
) -> None:
    client, store = client_and_store
    result = {
        "score": 7,
        "strengths": ["Good structure."],
        "gaps": ["Missing context."],
        "missing_points": ["Edge case"],
        "suggested_addition": "Consider X.",
        "follow_up_question": None,
    }
    store.load_session.return_value = _session([_attempt(result=result)])

    response = client.get("/ui/my-context/sessions/abc123")

    assert "Good structure." in response.text
    assert "Missing context." in response.text
    assert "Edge case" in response.text
    assert "Consider X." in response.text


def test_get_session_results_malformed_result_json_still_renders(
    client_and_store: tuple[TestClient, MagicMock],
) -> None:
    client, store = client_and_store
    attempt = _attempt(score=6)
    attempt.result_json = "not valid json {"
    store.load_session.return_value = _session([attempt])

    response = client.get("/ui/my-context/sessions/abc123")

    assert response.status_code == 200
    assert "6/10" in response.text
