from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    with (
        patch("learning_tool.api.main.create_stores"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore"),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        yield c


def test_get_admin_index_returns_200(client: TestClient) -> None:
    response = client.get("/admin")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_admin_index_links_to_annotations(client: TestClient) -> None:
    response = client.get("/admin")

    assert "/admin/annotations" in response.text
