from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.models import BankQuestion


def _make_client(
    mock_bank_store: MagicMock, mock_session_store: MagicMock
) -> Generator[tuple[TestClient, MagicMock, MagicMock]]:
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.main.Retriever"),
        patch("learning_tool.api.main.QuestionBankStore", return_value=mock_bank_store),
        patch("learning_tool.api.main.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c, mock_bank_store, mock_session_store


@pytest.fixture()
def client_next_question() -> Generator[tuple[TestClient, MagicMock, MagicMock]]:
    mock_bank_store = MagicMock()
    mock_bank_store.get_random.return_value = BankQuestion.from_parts(
        "History", "Who was Napoleon?"
    )
    mock_session_store = MagicMock()
    mock_session_store.record.return_value = 42
    yield from _make_client(mock_bank_store, mock_session_store)


@pytest.fixture()
def client_bank_exhausted() -> Generator[tuple[TestClient, MagicMock, MagicMock]]:
    mock_bank_store = MagicMock()
    mock_bank_store.get_random.return_value = None
    mock_session_store = MagicMock()
    mock_session_store.record.return_value = 1
    yield from _make_client(mock_bank_store, mock_session_store)


def test_post_submit_records_attempt_with_none_score(
    client_next_question: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, _, mock_session_store = client_next_question

    client.post(
        "/ui/myctx/submit",
        data={
            "question": "What is X?",
            "answer": "It is Y.",
            "question_id": "qid-1",
            "query": "History",
            "session_id": "sess-1",
        },
    )

    mock_session_store.record.assert_called_once()
    # record is called positionally: (session_id, question, answer, score, question_id, result_json)
    assert mock_session_store.record.call_args[0][3] is None


def test_post_submit_returns_next_question(
    client_next_question: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, _, _ = client_next_question

    response = client.post(
        "/ui/myctx/submit",
        data={
            "question": "What is X?",
            "answer": "It is Y.",
            "question_id": "qid-1",
            "query": "History",
            "session_id": "sess-1",
        },
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Who was Napoleon?" in response.text


def test_post_submit_returns_bank_empty_when_exhausted(
    client_bank_exhausted: tuple[TestClient, MagicMock, MagicMock],
) -> None:
    client, _, _ = client_bank_exhausted

    response = client.post(
        "/ui/myctx/submit",
        data={
            "question": "What is X?",
            "answer": "It is Y.",
            "question_id": "qid-1",
            "query": "History",
            "session_id": "sess-1",
        },
    )

    assert response.status_code == 200
    assert "No questions in the bank" in response.text
