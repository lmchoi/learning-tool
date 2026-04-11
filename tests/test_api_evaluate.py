from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.models import EvaluationResult


@pytest.fixture()
def mock_retriever() -> Generator[MagicMock]:
    with patch("learning_tool.api.main.Retriever") as mock_cls:
        yield mock_cls.return_value


@pytest.fixture()
def client(mock_retriever: MagicMock) -> Generator[TestClient]:
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c


def test_post_evaluate_returns_200(client: TestClient, mock_retriever: MagicMock) -> None:
    evaluation = EvaluationResult(
        score=7,
        strengths=["Good point."],
        gaps=["Missed ATP."],
        missing_points=["ATP synthesis"],
        suggested_addition="Mention ATP synthase.",
        follow_up_question="How does the electron transport chain work?",
    )
    mock_retriever.retrieve.return_value = [("chunk one", 0.9)]
    with patch("learning_tool.api.main.evaluate_answer", new=AsyncMock(return_value=evaluation)):
        response = client.post(
            "/contexts/biology/evaluate",
            json={
                "query": "mitochondria",
                "question": "What is the role of mitochondria?",
                "answer": "They produce energy.",
            },
        )

    assert response.status_code == 200
    assert response.json()["score"] == 7
    assert response.json()["strengths"] == ["Good point."]


def test_post_evaluate_returns_422_when_body_incomplete(client: TestClient) -> None:
    response = client.post(
        "/contexts/biology/evaluate",
        json={"query": "mitochondria", "question": "What is it?"},  # missing answer
    )
    assert response.status_code == 422


def test_post_evaluate_returns_404_for_unknown_context(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.side_effect = FileNotFoundError("no store")
    response = client.post(
        "/contexts/unknown/evaluate",
        json={"query": "topic", "question": "Q?", "answer": "A."},
    )

    assert response.status_code == 404
    assert "unknown" in response.json()["detail"]
