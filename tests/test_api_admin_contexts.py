from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
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


def test_get_admin_contexts_returns_200(client: TestClient) -> None:
    response = client.get("/admin/contexts")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_admin_contexts_renders_form(client: TestClient) -> None:
    response = client.get("/admin/contexts")

    assert "<form" in response.text
    assert 'name="name"' in response.text
