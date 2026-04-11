from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app


@pytest.fixture()
def mock_session_store() -> MagicMock:
    store = MagicMock()
    return store


@pytest.fixture()
def client(tmp_path: Path, mock_session_store: MagicMock) -> Generator[TestClient]:
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


def test_get_report_form_returns_200(client: TestClient) -> None:
    response = client.get("/report-evaluation/form?question_id=test-qid&context_name=ctx")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "textarea" in response.text


def test_post_report_evaluation_records_annotation(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    response = client.post(
        "/report-evaluation",
        data={
            "question_id": "test-qid",
            "context_name": "ctx",
            "comment": "This feedback missed the point entirely.",
        },
    )

    assert response.status_code == 200
    assert "Thanks, reported." in response.text
    mock_session_store.record_annotation.assert_called_once_with(
        "test-qid", "evaluation", "down", "This feedback missed the point entirely."
    )


def test_post_report_evaluation_requires_comment(client: TestClient) -> None:
    response = client.post(
        "/report-evaluation",
        data={"question_id": "test-qid", "context_name": "ctx", "comment": ""},
    )
    assert response.status_code == 422


def test_post_report_evaluation_rejects_whitespace_comment(
    client: TestClient,
) -> None:
    response = client.post(
        "/report-evaluation",
        data={"question_id": "test-qid", "context_name": "ctx", "comment": "   "},
    )
    assert response.status_code == 422
