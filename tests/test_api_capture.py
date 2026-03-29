from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.models import BankQuestion, ContextMetadata
from core.session.models import QuestionAttempt, SessionRecord
from core.session.store import SessionStore


def _make_client(
    mock_bank_store: MagicMock, mock_session_store: MagicMock
) -> Generator[TestClient]:
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.Retriever"),
        patch("api.main.QuestionBankStore", return_value=mock_bank_store),
        patch("api.main.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c


QUESTION = BankQuestion.from_parts("Async", "What is an event loop?")
METADATA = ContextMetadata(goal="Learn Python", focus_areas=["Async"])


def _mock_bank(question: BankQuestion | None = QUESTION) -> MagicMock:
    store = MagicMock()
    store.get_random.return_value = question
    return store


def _mock_session(session_id: str = "sess-abc") -> MagicMock:
    store = MagicMock()
    store.start_session.return_value = session_id
    return store


@pytest.fixture()
def client() -> Generator[TestClient]:
    yield from _make_client(_mock_bank(), _mock_session())


@pytest.fixture()
def client_empty_bank() -> Generator[TestClient]:
    yield from _make_client(_mock_bank(None), _mock_session())


# --- GET /ui/{context}/capture ---


def test_get_capture_returns_200(client: TestClient) -> None:
    response = client.get("/ui/myctx/capture")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_capture_shows_question_text(client: TestClient) -> None:
    response = client.get("/ui/myctx/capture")

    assert "What is an event loop?" in response.text


def test_get_capture_includes_answer_textarea(client: TestClient) -> None:
    response = client.get("/ui/myctx/capture")

    assert "textarea" in response.text
    assert 'name="answer"' in response.text


def test_get_capture_passes_session_id_in_form(client: TestClient) -> None:
    response = client.get("/ui/myctx/capture")

    assert 'name="session_id"' in response.text
    assert "sess-abc" in response.text


def test_get_capture_passes_question_id_in_form(client: TestClient) -> None:
    response = client.get("/ui/myctx/capture")

    assert 'name="question_id"' in response.text


def test_get_capture_includes_export_link(client: TestClient) -> None:
    response = client.get("/ui/myctx/capture")

    assert "/ui/myctx/capture/export" in response.text


def test_get_capture_returns_404_when_bank_empty(client_empty_bank: TestClient) -> None:
    response = client_empty_bank.get("/ui/myctx/capture")

    assert response.status_code == 404


def test_get_capture_creates_session(client: TestClient) -> None:
    mock_session = _mock_session()
    for c in _make_client(_mock_bank(), mock_session):
        c.get("/ui/myctx/capture")
        mock_session.start_session.assert_called_once()


# --- POST /ui/{context}/capture ---


def test_post_capture_returns_200(client: TestClient) -> None:
    response = client.post(
        "/ui/myctx/capture",
        data={
            "question": "What is an event loop?",
            "answer": "It drives async execution.",
            "session_id": "sess-abc",
            "question_id": QUESTION.id,
        },
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_post_capture_records_answer_with_score_zero(client: TestClient) -> None:
    mock_session = _mock_session()
    for c in _make_client(_mock_bank(), mock_session):
        c.post(
            "/ui/myctx/capture",
            data={
                "question": "What is an event loop?",
                "answer": "It drives async execution.",
                "session_id": "sess-abc",
                "question_id": QUESTION.id,
            },
        )
    mock_session.record.assert_called_once_with(
        "sess-abc", "What is an event loop?", "It drives async execution.", 0, QUESTION.id, None
    )


def test_post_capture_shows_next_question(client: TestClient) -> None:
    response = client.post(
        "/ui/myctx/capture",
        data={
            "question": "What is an event loop?",
            "answer": "It drives async execution.",
            "session_id": "sess-abc",
        },
    )

    assert "What is an event loop?" in response.text  # next question (same mock returns same)


def test_post_capture_shows_export_link_when_bank_empty(client_empty_bank: TestClient) -> None:
    # Bank returns None on get_random — session.record is still mocked to return something
    mock_session = _mock_session()
    mock_session.record.return_value = 1
    for c in _make_client(_mock_bank(None), mock_session):
        response = c.post(
            "/ui/myctx/capture",
            data={
                "question": "What is an event loop?",
                "answer": "It drives async execution.",
                "session_id": "sess-abc",
            },
        )
    assert "/ui/myctx/capture/export" in response.text


# --- GET /ui/{context}/capture/export ---


def _session_record(session_id: str = "sess-abc") -> SessionRecord:
    return SessionRecord(
        session_id=session_id,
        context="myctx",
        started_at="2026-01-01T00:00:00+00:00",
        attempts=[
            QuestionAttempt(
                session_id=session_id,
                question_id="qid-1",
                question_text="What is an event loop?",
                answer_text="It drives async execution.",
                score=0,
                timestamp="2026-01-01T00:00:00+00:00",
            ),
            QuestionAttempt(
                session_id=session_id,
                question_id="qid-2",
                question_text="What is asyncio.gather?",
                answer_text="Runs coroutines concurrently.",
                score=0,
                timestamp="2026-01-01T00:01:00+00:00",
            ),
        ],
    )


def test_get_capture_export_returns_200() -> None:
    mock_session = _mock_session()
    mock_session.load_session.return_value = _session_record()
    for c in _make_client(_mock_bank(), mock_session):
        app.state.context_store = MagicMock()
        app.state.context_store.load_context.return_value = METADATA
        response = c.get("/ui/myctx/capture/export?session_id=sess-abc")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_capture_export_contains_question_text() -> None:
    mock_session = _mock_session()
    mock_session.load_session.return_value = _session_record()
    for c in _make_client(_mock_bank(), mock_session):
        app.state.context_store = MagicMock()
        app.state.context_store.load_context.return_value = METADATA
        response = c.get("/ui/myctx/capture/export?session_id=sess-abc")

    assert "What is an event loop?" in response.text


def test_get_capture_export_contains_answer_text() -> None:
    mock_session = _mock_session()
    mock_session.load_session.return_value = _session_record()
    for c in _make_client(_mock_bank(), mock_session):
        app.state.context_store = MagicMock()
        app.state.context_store.load_context.return_value = METADATA
        response = c.get("/ui/myctx/capture/export?session_id=sess-abc")

    assert "It drives async execution." in response.text


def test_get_capture_export_contains_all_qa_pairs() -> None:
    mock_session = _mock_session()
    mock_session.load_session.return_value = _session_record()
    for c in _make_client(_mock_bank(), mock_session):
        app.state.context_store = MagicMock()
        app.state.context_store.load_context.return_value = METADATA
        response = c.get("/ui/myctx/capture/export?session_id=sess-abc")

    assert "What is asyncio.gather?" in response.text
    assert "Runs coroutines concurrently." in response.text


def test_get_capture_export_contains_format_instructions() -> None:
    mock_session = _mock_session()
    mock_session.load_session.return_value = _session_record()
    for c in _make_client(_mock_bank(), mock_session):
        app.state.context_store = MagicMock()
        app.state.context_store.load_context.return_value = METADATA
        response = c.get("/ui/myctx/capture/export?session_id=sess-abc")

    assert "question_id" in response.text
    assert "score" in response.text


async def _mock_async_gen(value: None) -> AsyncIterator[None]:
    yield value


def test_get_capture_export_contains_paste_back_form(tmp_path: Path) -> None:
    # use a temp store dir to avoid test pollution
    (tmp_path / "my-ctx").mkdir(parents=True, exist_ok=True)
    store = SessionStore(tmp_path, "my-ctx")
    sid = store.start_session()
    store.record(sid, "Q1", "A1", 0)

    # Mock lifespan and override store_dir
    lifespan_mock = asynccontextmanager(lambda _: _mock_async_gen(None))
    with (
        patch("api.main.app.router.lifespan_context", lifespan_mock),
        patch("api.main.STORE_DIR", tmp_path),
        TestClient(app) as client,
    ):
        # Cast to Any to satisfy mypy for state access on TestClient app
        any_app: Any = client.app
        any_app.state.store_dir = tmp_path
        resp = client.get(f"/ui/my-ctx/capture/export?session_id={sid}")
        assert resp.status_code == 200
        assert 'action="/ui/my-ctx/capture/paste-back"' in resp.text
        assert 'name="evaluation_text"' in resp.text
        assert "Import scores" in resp.text


def test_get_capture_export_returns_404_for_unknown_session() -> None:
    mock_session = _mock_session()
    mock_session.load_session.return_value = None
    for c in _make_client(_mock_bank(), mock_session):
        response = c.get("/ui/myctx/capture/export?session_id=no-such-session")

    assert response.status_code == 404


# --- SessionStore.load_session ---


def test_load_session_returns_session_with_attempts(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    store.record(session_id, "What is X?", "It is Y.", 0, question_id="qid-1")

    session = store.load_session(session_id)

    assert session is not None
    assert session.session_id == session_id
    assert len(session.attempts) == 1
    assert session.attempts[0].question_text == "What is X?"
    assert session.attempts[0].answer_text == "It is Y."
    assert session.attempts[0].score == 0
    assert session.attempts[0].question_id == "qid-1"


def test_load_session_returns_none_for_unknown_id(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")

    result = store.load_session("nonexistent-id")

    assert result is None
