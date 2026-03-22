from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def mock_session_store() -> MagicMock:
    store = MagicMock()
    return store


@pytest.fixture()
def client(tmp_path: Path, mock_session_store: MagicMock) -> Generator[TestClient]:
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.SessionStore", return_value=mock_session_store),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


def test_get_admin_annotations_returns_200(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotations.return_value = []
    response = client.get("/admin/annotations?context_name=ctx")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_admin_annotations_shows_no_annotations_message(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotations.return_value = []
    response = client.get("/admin/annotations?context_name=ctx")
    assert "No annotations found" in response.text


def test_get_admin_annotations_shows_annotation_card(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotations.return_value = [
        {
            "id": 1,
            "attempt_id": 1,
            "target_type": "evaluation",
            "sentiment": "down",
            "comment": "Wrong feedback",
            "created_at": "2026-03-21T10:00:00+00:00",
            "question_text": "What is ATP?",
            "answer_text": "Energy currency.",
            "score": 5,
            "result_json": (
                '{"score": 5, "gaps": ["Missed synthesis"], "strengths": [],'
                ' "missing_points": [], "suggested_addition": null, "follow_up_question": "How?"}'
            ),
            "chunks": ["chunk one"],
        }
    ]
    response = client.get("/admin/annotations?context_name=ctx")
    assert "What is ATP?" in response.text
    assert "Wrong feedback" in response.text
    assert "Missed synthesis" in response.text


def test_get_admin_annotations_passes_filters(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotations.return_value = []
    client.get("/admin/annotations?context_name=ctx&target_type=evaluation&sentiment=down")
    mock_session_store.load_annotations.assert_called_once_with(
        target_type="evaluation", sentiment="down", flagged=False
    )


def test_get_admin_annotations_empty_filters_pass_none(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotations.return_value = []
    client.get("/admin/annotations?context_name=ctx")
    mock_session_store.load_annotations.assert_called_once_with(
        target_type=None, sentiment=None, flagged=False
    )


def test_get_admin_annotations_flagged_filter(
    client: TestClient, mock_session_store: MagicMock
) -> None:
    mock_session_store.load_annotations.return_value = []
    client.get("/admin/annotations?context_name=ctx&flagged=true")
    mock_session_store.load_annotations.assert_called_once_with(
        target_type=None, sentiment=None, flagged=True
    )
