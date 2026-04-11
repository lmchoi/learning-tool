from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.models import BankQuestion


def _make_client(mock_bank_store: MagicMock) -> Generator[tuple[TestClient, MagicMock]]:
    with (
        patch("learning_tool.api.main.create_stores"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.QuestionBankStore", return_value=mock_bank_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        yield c, mock_bank_store


@pytest.fixture()
def client_with_question() -> Generator[TestClient]:
    mock_store = MagicMock()
    mock_store.get_random.return_value = BankQuestion.from_parts(
        "Agent Development", "What is an agent loop?"
    )
    for client, _ in _make_client(mock_store):
        yield client


@pytest.fixture()
def client_empty_bank() -> Generator[TestClient]:
    mock_store = MagicMock()
    mock_store.get_random.return_value = None
    for client, _ in _make_client(mock_store):
        yield client


@pytest.fixture()
def client_with_question_and_mock() -> Generator[tuple[TestClient, MagicMock]]:
    mock_store = MagicMock()
    mock_store.get_random.return_value = BankQuestion.from_parts(
        "Agent Development", "What is an agent loop?"
    )
    yield from _make_client(mock_store)


def test_get_bank_question_returns_question(client_with_question: TestClient) -> None:
    response = client_with_question.get("/contexts/myctx/questions?pick=random")

    assert response.status_code == 200
    body = response.json()
    assert body["question"]["focus_area"] == "Agent Development"
    assert body["question"]["question"] == "What is an agent loop?"
    assert "id" in body["question"]


def test_get_bank_question_passes_focus_area_to_store(
    client_with_question_and_mock: tuple[TestClient, MagicMock],
) -> None:
    client, mock_store = client_with_question_and_mock
    client.get("/contexts/myctx/questions?pick=random&focus_area=Agent+Development")

    mock_store.get_random.assert_called_with("Agent Development")


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


def test_get_bank_question_fragment_returns_question_html(client_with_question: TestClient) -> None:
    response = client_with_question.get(
        "/ui/myctx/question/bank?focus_area=Agent+Development&session_id=sess-1"
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "What is an agent loop?" in response.text


def test_get_bank_question_fragment_returns_generate_prompt_when_empty(
    client_empty_bank: TestClient,
) -> None:
    response = client_empty_bank.get(
        "/ui/myctx/question/bank?focus_area=Agent+Development&session_id=sess-1"
    )

    assert response.status_code == 200
    assert "Generate a question" in response.text


def test_get_bank_question_fragment_generate_button_links_to_generation_endpoint(
    client_empty_bank: TestClient,
) -> None:
    response = client_empty_bank.get(
        "/ui/myctx/question/bank?focus_area=Agent+Development&session_id=sess-1"
    )

    assert "/ui/myctx/question" in response.text


def test_get_bank_question_fragment_skip_links_to_bank_endpoint(
    client_with_question: TestClient,
) -> None:
    response = client_with_question.get(
        "/ui/myctx/question/bank?focus_area=Agent+Development&session_id=sess-1"
    )

    assert "/ui/myctx/question/bank" in response.text


def test_get_bank_question_fragment_form_posts_to_submit(
    client_with_question: TestClient,
) -> None:
    response = client_with_question.get(
        "/ui/myctx/question/bank?focus_area=Agent+Development&session_id=sess-1"
    )

    assert "/ui/myctx/submit" in response.text
