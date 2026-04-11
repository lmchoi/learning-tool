import logging
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


def test_middleware_logs_request(
    client: TestClient, mock_retriever: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    question = Question(text="What is osmosis?")
    mock_retriever.retrieve.return_value = [("chunk", 0.9)]
    with (
        patch(
            "learning_tool.api.routers.api.generate_question_gemini",
            new=AsyncMock(return_value=question),
        ),
        caplog.at_level(logging.INFO, logger="learning_tool.api.main"),
    ):
        response = client.get("/contexts/biology/question?query=osmosis")

    assert response.status_code == 200
    assert any(
        "GET" in m and "/contexts/biology/question" in m and "200" in m for m in caplog.messages
    )


def test_404_emits_warning(
    client: TestClient, mock_retriever: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    mock_retriever.retrieve.side_effect = FileNotFoundError("no store")
    with caplog.at_level(logging.WARNING, logger="learning_tool.api.main"):
        response = client.get("/contexts/unknown/question?query=anything")

    assert response.status_code == 404
    assert any(r.levelno == logging.WARNING and "unknown" in r.getMessage() for r in caplog.records)
