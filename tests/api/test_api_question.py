from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.models import Question


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


def test_get_question_returns_200(client: TestClient, mock_retriever: MagicMock) -> None:
    question = Question(text="What is the capital of France?")
    mock_retriever.retrieve.return_value = [("chunk one", 0.9), ("chunk two", 0.8)]
    with patch(
        "learning_tool.api.routers.endpoints.generate_question_gemini",
        new=AsyncMock(return_value=question),
    ):
        response = client.get("/contexts/geography/question?query=capitals")

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "What is the capital of France?"
    assert isinstance(body["question_id"], str) and len(body["question_id"]) == 36  # UUID


def test_get_question_returns_404_for_unknown_context(
    client: TestClient, mock_retriever: MagicMock
) -> None:
    mock_retriever.retrieve.side_effect = FileNotFoundError("no store")
    response = client.get("/contexts/unknown/question?query=anything")

    assert response.status_code == 404
    assert "unknown" in response.json()["detail"]


def test_get_question_returns_422_when_query_missing(client: TestClient) -> None:
    response = client.get("/contexts/geography/question")

    assert response.status_code == 422
