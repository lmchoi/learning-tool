from collections.abc import Generator
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from learning_tool.core.ingestion.store import ContextStore
from tests.conftest import make_api_client


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    (tmp_path / "my-context").mkdir()
    (tmp_path / "my-context" / "context.yaml").write_text(
        yaml.dump({"goal": "Learn Python basics", "focus_areas": []})
    )
    yield from make_api_client(tmp_path)


# --- POST /ui/contexts/{name}/archive ---


def test_post_archive_returns_200(client: TestClient) -> None:
    # Must be 200 (not 204) — HTMX 2.x ignores 204 responses entirely,
    # so hx-swap="delete" would not fire.
    response = client.post("/ui/contexts/my-context/archive")

    assert response.status_code == 200


def test_post_archive_returns_empty_response(client: TestClient) -> None:
    response = client.post("/ui/contexts/my-context/archive")

    assert response.text.strip() == ""


def test_post_archive_sets_archived_in_store(client: TestClient, tmp_path: Path) -> None:
    client.post("/ui/contexts/my-context/archive")

    store = ContextStore(tmp_path)
    loaded = store.load_context("my-context")
    assert loaded is not None
    assert loaded.archived is True


def test_post_archive_missing_context_returns_404(client: TestClient) -> None:
    response = client.post("/ui/contexts/no-such-context/archive")

    assert response.status_code == 404
