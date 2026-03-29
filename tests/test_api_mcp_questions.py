from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.models import BankQuestion


def _make_client(
    mock_bank_store: MagicMock, store_exists: bool = True
) -> Generator[tuple[TestClient, MagicMock]]:
    mock_exists = MagicMock(return_value=store_exists)
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.Retriever"),
        patch("api.main.QuestionBankStore", return_value=mock_bank_store),
        patch("api.main.Path.exists", mock_exists),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c, mock_bank_store


@pytest.fixture()
def client_with_question() -> Generator[tuple[TestClient, MagicMock]]:
    mock_store = MagicMock()
    mock_store.get_random.return_value = BankQuestion.from_parts("biology", "What is a cell?")
    yield from _make_client(mock_store)


@pytest.fixture()
def client_empty_bank() -> Generator[tuple[TestClient, MagicMock]]:
    mock_store = MagicMock()
    mock_store.get_random.return_value = None
    yield from _make_client(mock_store)


@pytest.fixture()
def client_no_context() -> Generator[tuple[TestClient, MagicMock]]:
    mock_store = MagicMock()
    yield from _make_client(mock_store, store_exists=False)


def test_get_api_question_success(
    client_with_question: tuple[TestClient, MagicMock],
) -> None:
    client, _ = client_with_question
    response = client.get("/api/questions/biology")

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "What is a cell?"
    assert body["focus_area"] == "biology"
    assert "question_id" in body


def test_get_api_question_with_focus_area(
    client_with_question: tuple[TestClient, MagicMock],
) -> None:
    client, mock_store = client_with_question
    response = client.get("/api/questions/biology?focus_area=mitochondria")

    assert response.status_code == 200
    body = response.json()
    assert body["focus_area"] == "biology"  # returned from MockStore
    mock_store.get_random.assert_called_with("mitochondria")


def test_get_api_question_404_empty_bank(
    client_empty_bank: tuple[TestClient, MagicMock],
) -> None:
    client, _ = client_empty_bank
    response = client.get("/api/questions/biology")

    assert response.status_code == 404
    assert "No questions found" in response.json()["detail"]


def test_get_api_question_404_no_context(
    client_no_context: tuple[TestClient, MagicMock],
) -> None:
    client, _ = client_no_context
    response = client.get("/api/questions/unknown")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
