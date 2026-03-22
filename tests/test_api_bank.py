from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.models import BankQuestion


def _make_client(mock_bank_store: MagicMock) -> Generator[TestClient]:
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.Retriever"),
        patch("api.main.QuestionBankStore", return_value=mock_bank_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c


@pytest.fixture()
def client_with_question() -> Generator[TestClient]:
    mock_store = MagicMock()
    mock_store.get_random.return_value = BankQuestion.from_parts(
        "Agent Development", "What is an agent loop?"
    )
    yield from _make_client(mock_store)


@pytest.fixture()
def client_empty_bank() -> Generator[TestClient]:
    mock_store = MagicMock()
    mock_store.get_random.return_value = None
    yield from _make_client(mock_store)


def test_get_bank_question_returns_question(client_with_question: TestClient) -> None:
    response = client_with_question.get("/contexts/myctx/questions?pick=random")

    assert response.status_code == 200
    body = response.json()
    assert body["question"]["focus_area"] == "Agent Development"
    assert body["question"]["question"] == "What is an agent loop?"
    assert "id" in body["question"]


def test_get_bank_question_returns_null_when_empty(client_empty_bank: TestClient) -> None:
    response = client_empty_bank.get("/contexts/myctx/questions?pick=random")

    assert response.status_code == 200
    assert response.json() == {"question": None}


def test_get_bank_question_returns_422_without_pick(client_empty_bank: TestClient) -> None:
    response = client_empty_bank.get("/contexts/myctx/questions")

    assert response.status_code == 422


def test_get_bank_question_returns_422_for_invalid_pick(client_empty_bank: TestClient) -> None:
    response = client_empty_bank.get("/contexts/myctx/questions?pick=list")

    assert response.status_code == 422
