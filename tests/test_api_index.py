from collections.abc import Generator
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from api.main import app
from core.ingestion.store import ContextStore


def _make_client(store_dir: Path) -> Generator[TestClient]:
    with ExitStack() as stack:
        stack.enter_context(patch("api.main.SentenceTransformerEmbedder"))
        stack.enter_context(patch("api.main.AsyncAnthropic"))
        stack.enter_context(patch("api.main.genai"))
        stack.enter_context(patch("api.main.SessionStore"))
        stack.enter_context(patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}))
        c = stack.enter_context(TestClient(app))
        c.app.state.store_dir = store_dir  # type: ignore[attr-defined]
        c.app.state.context_store = ContextStore(store_dir)  # type: ignore[attr-defined]
        yield c


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    (tmp_path / "python").mkdir()
    (tmp_path / "sql").mkdir()
    (tmp_path / "python" / "context.yaml").write_text(
        yaml.dump({"goal": "Master Python fundamentals", "focus_areas": []})
    )
    # sql has no context.yaml — exercises the missing-yaml path
    yield from _make_client(tmp_path)


@pytest.fixture()
def empty_store_client(tmp_path: Path) -> Generator[TestClient]:
    yield from _make_client(tmp_path)


@pytest.fixture()
def missing_store_client(tmp_path: Path) -> Generator[TestClient]:
    yield from _make_client(tmp_path / "nonexistent")


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

    assert 'href="/admin"' in response.text


def test_get_index_empty_store_shows_no_contexts(empty_store_client: TestClient) -> None:
    response = empty_store_client.get("/")

    assert response.status_code == 200
    assert "/ui/" not in response.text


def test_get_index_missing_store_dir_shows_no_contexts(missing_store_client: TestClient) -> None:
    response = missing_store_client.get("/")

    assert response.status_code == 200
    assert "/ui/" not in response.text


def test_get_index_shows_context_goal(client: TestClient) -> None:
    response = client.get("/")

    assert "Master Python fundamentals" in response.text


def test_get_index_missing_yaml_shows_placeholder(client: TestClient) -> None:
    response = client.get("/")

    # sql has no context.yaml — a placeholder should appear instead of the goal text
    assert "No goal set" in response.text
