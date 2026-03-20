from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def mock_retriever() -> Generator[MagicMock]:
    with patch("api.main.Retriever") as mock_cls:
        yield mock_cls.return_value


@pytest.fixture()
def client(mock_retriever: MagicMock) -> Generator[TestClient]:
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        TestClient(app) as c,
    ):
        yield c


def test_get_ui_returns_200(client: TestClient) -> None:
    response = client.get("/ui/my-context")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_ui_includes_htmx(client: TestClient) -> None:
    response = client.get("/ui/my-context")

    assert "htmx.org" in response.text


def test_get_ui_includes_context_name(client: TestClient) -> None:
    response = client.get("/ui/my-context")

    assert "my-context" in response.text
