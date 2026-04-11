from collections.abc import Generator
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from tests.conftest import make_api_client


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    (tmp_path / "python").mkdir()
    (tmp_path / "sql").mkdir()
    (tmp_path / "python" / "context.yaml").write_text(
        yaml.dump({"goal": "Master Python fundamentals", "focus_areas": []})
    )
    # sql has no context.yaml — exercises the missing-yaml path
    yield from make_api_client(tmp_path)


@pytest.fixture()
def empty_store_client(tmp_path: Path) -> Generator[TestClient]:
    yield from make_api_client(tmp_path)


@pytest.fixture()
def missing_store_client(tmp_path: Path) -> Generator[TestClient]:
    yield from make_api_client(tmp_path / "nonexistent")


def test_get_index_returns_200(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_get_index_lists_context_links(client: TestClient) -> None:
    response = client.get("/")

    # python has a context.yaml — should appear
    assert "/ui/python" in response.text
    # sql has no context.yaml — should be hidden
    assert "/ui/sql" not in response.text


def test_get_index_links_to_admin(client: TestClient) -> None:
    response = client.get("/")

    assert 'href="/admin"' in response.text


def test_get_index_empty_store_shows_no_contexts(empty_store_client: TestClient) -> None:
    response = empty_store_client.get("/")

    assert response.status_code == 200
    assert "context-card" not in response.text


def test_get_index_missing_store_dir_shows_no_contexts(missing_store_client: TestClient) -> None:
    response = missing_store_client.get("/")

    assert response.status_code == 200
    assert "context-card" not in response.text


def test_get_index_shows_context_goal(client: TestClient) -> None:
    response = client.get("/")

    assert "Master Python fundamentals" in response.text


def test_get_index_missing_yaml_not_shown(client: TestClient) -> None:
    response = client.get("/")

    # sql has no context.yaml — should be hidden entirely, not shown with placeholder
    assert "No goal set" not in response.text


def test_get_index_shows_new_context_widget(client: TestClient) -> None:
    response = client.get("/")

    assert 'id="new-context-widget"' in response.text


def test_get_index_new_context_button_has_htmx_attributes(client: TestClient) -> None:
    response = client.get("/")

    assert 'hx-get="/ui/_new-context-form"' in response.text


@pytest.fixture()
def archived_store_client(tmp_path: Path) -> Generator[TestClient]:
    (tmp_path / "active").mkdir()
    (tmp_path / "archived-ctx").mkdir()
    (tmp_path / "active" / "context.yaml").write_text(
        yaml.dump({"goal": "active goal", "focus_areas": [], "archived": False})
    )
    (tmp_path / "archived-ctx" / "context.yaml").write_text(
        yaml.dump({"goal": "archived goal", "focus_areas": [], "archived": True})
    )
    yield from make_api_client(tmp_path)


def test_get_index_excludes_archived_contexts(archived_store_client: TestClient) -> None:
    response = archived_store_client.get("/")

    assert "active goal" in response.text
    assert "archived goal" not in response.text
