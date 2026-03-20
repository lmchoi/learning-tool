from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.models import EvaluationResult, Question


@pytest.fixture()
def mock_retriever() -> Generator[MagicMock]:
    with patch("api.main.Retriever") as mock_cls:
        yield mock_cls.return_value


@pytest.fixture()
def client(mock_retriever: MagicMock) -> Generator[TestClient]:
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
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


def test_get_question_fragment_returns_200(client: TestClient, mock_retriever: MagicMock) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_question_fragment_contains_question_text(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic")

    assert "What is X?" in response.text


def test_get_question_fragment_contains_answer_form(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic")

    assert "hx-post" in response.text
    assert "textarea" in response.text


def test_get_question_fragment_passes_query_to_form(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch(
        "api.main.generate_question", new=AsyncMock(return_value=Question(text="What is X?"))
    ):
        response = client.get("/ui/my-context/question?query=topic")

    assert 'name="query"' in response.text
    assert 'value="topic"' in response.text


def test_post_evaluate_fragment_returns_200(client: TestClient, mock_retriever: MagicMock) -> None:
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with patch("api.main.evaluate_answer", new=AsyncMock(return_value=EVALUATION)):
        response = client.post(
            "/ui/my-context/evaluate",
            data={"question": "What is X?", "answer": "It is Y.", "query": "topic"},
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
            data={"question": "What is X?", "answer": "It is Y.", "query": "topic"},
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
            data={"question": "What is X?", "answer": "It is Y.", "query": "topic"},
        )

    mock_retriever.retrieve.assert_called_once_with("my-context", "topic", k=5)
