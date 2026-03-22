from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import _get_session_store, app
from core.models import ContextMetadata, EvaluationResult, Question
from core.session.store import SessionStore


@pytest.fixture()
def mock_retriever() -> Generator[MagicMock]:
    with patch("api.main.Retriever") as mock_cls:
        yield mock_cls.return_value


@pytest.fixture()
def client(mock_retriever: MagicMock) -> Generator[TestClient]:
    mock_session_store = MagicMock()
    mock_session_store.start_session.return_value = "test-session-id"
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c


EVALUATION = EvaluationResult(
    score=8,
    strengths=["Clear explanation."],
    gaps=["Missed detail."],
    missing_points=["ATP"],
    suggested_addition=None,
    follow_up_question="What about X?",
)

METADATA = ContextMetadata(
    goal="Learn Python",
    focus_areas=["Async", "Type hints"],
)


def test_get_ui_returns_200(client: TestClient) -> None:
    response = client.get("/ui/my-context?query=topic")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_ui_includes_htmx(client: TestClient) -> None:
    response = client.get("/ui/my-context?query=topic")

    assert "htmx.org" in response.text


def test_get_ui_includes_context_name(client: TestClient) -> None:
    response = client.get("/ui/my-context?query=topic")

    assert "my-context" in response.text


def test_get_ui_triggers_question_load_on_page_load(client: TestClient) -> None:
    response = client.get("/ui/my-context?query=topic")

    assert "hx-get" in response.text
    assert "hx-trigger" in response.text


def test_get_ui_loads_from_bank_endpoint(client: TestClient) -> None:
    response = client.get("/ui/my-context?query=topic")

    assert "/ui/my-context/question/bank" in response.text


def test_get_ui_without_query_shows_focus_area_picker(client: TestClient) -> None:
    app.state.context_store = MagicMock()
    app.state.context_store.load_context.return_value = METADATA

    response = client.get("/ui/my-context")

    assert response.status_code == 200
    assert "Async" in response.text
    assert "Type hints" in response.text


def test_get_ui_without_query_returns_404_for_missing_context(client: TestClient) -> None:
    app.state.context_store = MagicMock()
    app.state.context_store.load_context.return_value = None

    response = client.get("/ui/missing-context")

    assert response.status_code == 404


def test_get_question_fragment_returns_200(client: TestClient, mock_retriever: MagicMock) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question_gemini", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic&session_id=test-session-id")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_question_fragment_contains_question_id(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question_gemini", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic&session_id=test-session-id")

    assert 'name="question_id"' in response.text


def test_get_question_fragment_contains_question_text(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question_gemini", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic&session_id=test-session-id")

    assert "What is X?" in response.text


def test_get_question_fragment_contains_answer_form(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question_gemini", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic&session_id=test-session-id")

    assert "hx-post" in response.text
    assert "textarea" in response.text


def test_get_question_fragment_passes_query_to_form(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question_gemini", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic&session_id=test-session-id")

    assert 'name="query"' in response.text
    assert 'value="topic"' in response.text


def test_post_evaluate_fragment_returns_200(client: TestClient, mock_retriever: MagicMock) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch("api.main.evaluate_answer", new=AsyncMock(return_value=EVALUATION)):
        response = client.post(
            "/ui/my-context/evaluate",
            data={
                "question": "What is X?",
                "answer": "It is Y.",
                "query": "topic",
                "session_id": "test-session-id",
            },
        )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_post_evaluate_fragment_contains_score(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch("api.main.evaluate_answer", new=AsyncMock(return_value=EVALUATION)):
        response = client.post(
            "/ui/my-context/evaluate",
            data={
                "question": "What is X?",
                "answer": "It is Y.",
                "query": "topic",
                "session_id": "test-session-id",
            },
        )

    assert "8" in response.text
    assert "Clear explanation." in response.text
    assert "What about X?" in response.text


def test_post_evaluate_fragment_uses_query_for_retrieval(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch("api.main.evaluate_answer", new=AsyncMock(return_value=EVALUATION)):
        client.post(
            "/ui/my-context/evaluate",
            data={
                "question": "What is X?",
                "answer": "It is Y.",
                "query": "topic",
                "session_id": "test-session-id",
            },
        )

    mock_retriever.retrieve.assert_called_once_with("my-context", "topic", k=5)


def test_get_question_fragment_returns_404_for_unknown_context(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.side_effect = FileNotFoundError("no store")
    response = client.get("/ui/unknown/question?query=topic&session_id=test-session-id")

    assert response.status_code == 404
    assert "unknown" in response.json()["detail"]


def test_post_evaluate_fragment_returns_404_for_unknown_context(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.side_effect = FileNotFoundError("no store")
    response = client.post(
        "/ui/unknown/evaluate",
        data={
            "question": "What is X?",
            "answer": "It is Y.",
            "query": "topic",
            "session_id": "test-session-id",
        },
    )

    assert response.status_code == 404
    assert "unknown" in response.json()["detail"]


def test_get_session_store_creates_instance_on_first_call(tmp_path: Path) -> None:
    cache: dict[str, SessionStore] = {}

    store = _get_session_store(cache, tmp_path, "python")

    assert isinstance(store, SessionStore)
    assert "python" in cache


def test_get_session_store_returns_same_instance_on_second_call(tmp_path: Path) -> None:
    cache: dict[str, SessionStore] = {}

    first = _get_session_store(cache, tmp_path, "python")
    second = _get_session_store(cache, tmp_path, "python")

    assert first is second


def test_get_session_store_creates_separate_instances_per_context(tmp_path: Path) -> None:
    cache: dict[str, SessionStore] = {}

    python_store = _get_session_store(cache, tmp_path, "python")
    sql_store = _get_session_store(cache, tmp_path, "sql")

    assert python_store is not sql_store
    assert len(cache) == 2
