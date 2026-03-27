from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    (tmp_path / "python").mkdir()
    (tmp_path / "sql").mkdir()
    from unittest.mock import patch

    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.SessionStore"),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


def test_get_index_returns_200(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_index_lists_context_links(client: TestClient) -> None:
    response = client.get("/")

    assert "/ui/python" in response.text
    assert "/ui/sql" in response.text


def test_get_index_links_to_admin(client: TestClient) -> None:
    response = client.get("/")

    assert "/admin" in response.text


def test_get_index_empty_store_shows_no_contexts(tmp_path: Path) -> None:
    from unittest.mock import patch

    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch("api.main.SessionStore"),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        response = c.get("/")

    assert response.status_code == 200
    assert "/ui/" not in response.text
