import json
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.session.models import QuestionAttempt, SessionRecord


@pytest.fixture()
def client() -> Generator[TestClient]:
    mock_session_store = MagicMock()
    with (
        patch("learning_tool.api.main.create_stores"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c


def _attempt(
    question: str = "What is X?",
    answer: str = "It is Y.",
    score: int | None = 7,
    result: dict[str, object] | None = None,
) -> QuestionAttempt:
    return QuestionAttempt(
        session_id="s1",
        question_text=question,
        answer_text=answer,
        score=score,
        timestamp="2026-03-25T10:00:00+00:00",
        result_json=json.dumps(result) if result else None,
    )


def _session(attempts: list[QuestionAttempt]) -> SessionRecord:
    return SessionRecord(
        session_id="s1",
        context="my-context",
        started_at="2026-03-25T09:00:00+00:00",
        attempts=attempts,
    )


def test_get_history_returns_200(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = []

    response = client.get("/ui/my-context/history")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_history_shows_empty_state(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = []

    response = client.get("/ui/my-context/history")

    assert "No sessions recorded yet" in response.text


def test_get_history_skips_sessions_with_no_attempts(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = [
        _session([]),  # empty session — should be hidden
    ]

    response = client.get("/ui/my-context/history")

    assert "No sessions recorded yet" in response.text


def test_get_history_shows_session_date(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = [_session([_attempt()])]

    response = client.get("/ui/my-context/history")

    assert "2026-03-25" in response.text


def test_get_history_shows_question_and_answer(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = [
        _session([_attempt(question="What is async?", answer="It is non-blocking.")])
    ]

    response = client.get("/ui/my-context/history")

    assert "What is async?" in response.text
    assert "It is non-blocking." in response.text


def test_get_history_shows_score(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = [
        _session([_attempt(score=8)])
    ]

    response = client.get("/ui/my-context/history")

    assert "8/10" in response.text


def test_get_history_shows_evaluation_breakdown(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    result = {
        "score": 7,
        "strengths": ["Good structure."],
        "gaps": ["Missing context."],
        "missing_points": ["Edge case"],
        "suggested_addition": "Consider X.",
        "follow_up_question": None,
    }
    app.state.session_stores["my-context"].load_sessions.return_value = [
        _session([_attempt(result=result)])
    ]

    response = client.get("/ui/my-context/history")

    assert "Good structure." in response.text
    assert "Missing context." in response.text
    assert "Edge case" in response.text
    assert "Consider X." in response.text


def test_get_history_coerces_string_fields_to_list(client: TestClient) -> None:
    """Existing DB records may have string values for list fields — coerce on load."""
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    result = {
        "score": 7,
        "strengths": "Good structure.",
        "gaps": "Missing context.",
        "missing_points": "Edge case",
        "suggested_addition": None,
        "follow_up_question": None,
    }
    app.state.session_stores["my-context"].load_sessions.return_value = [
        _session([_attempt(result=result)])
    ]

    response = client.get("/ui/my-context/history")

    assert "Good structure." in response.text
    assert "Missing context." in response.text
    assert "Edge case" in response.text


def test_get_history_malformed_result_json_falls_back_to_none(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    attempt = _attempt(score=6)
    attempt.result_json = "not valid json {"
    app.state.session_stores["my-context"].load_sessions.return_value = [_session([attempt])]

    response = client.get("/ui/my-context/history")

    assert response.status_code == 200
    assert "6/10" in response.text  # attempt still rendered, just no breakdown


def test_get_history_renders_unevaluated_attempt_without_500(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = [
        _session([_attempt(score=None)])
    ]

    response = client.get("/ui/my-context/history")

    assert response.status_code == 200
    assert "pending" in response.text


def test_get_history_avg_excludes_unevaluated_attempts(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = [
        _session([_attempt(score=8), _attempt(score=None)])
    ]

    response = client.get("/ui/my-context/history")

    assert response.status_code == 200
    assert "8.0/10" in response.text  # avg over scored attempts only


def test_get_history_shows_back_link(client: TestClient) -> None:
    app.state.session_stores = {}
    app.state.session_stores["my-context"] = MagicMock()
    app.state.session_stores["my-context"].load_sessions.return_value = []

    response = client.get("/ui/my-context/history")

    assert "/ui/my-context" in response.text
