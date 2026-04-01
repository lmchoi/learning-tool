from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def client() -> Generator[TestClient]:
    with (
        patch("api.main.SentenceTransformerEmbedder"),
        patch("api.main.AsyncAnthropic"),
        patch("api.main.genai"),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app, follow_redirects=False) as c,
    ):
        yield c


# --- POST /ui/contexts ---


def test_post_contexts_valid_name_returns_hx_redirect(client: TestClient) -> None:
    response = client.post("/ui/contexts", data={"name": "my-context"})

    assert response.headers.get("HX-Redirect") == "/ui/my-context/setup"


def test_post_contexts_valid_name_returns_200(client: TestClient) -> None:
    response = client.post("/ui/contexts", data={"name": "my-context"})

    assert response.status_code == 200


def test_post_contexts_invalid_name_returns_400(client: TestClient) -> None:
    response = client.post("/ui/contexts", data={"name": "NO"})

    assert response.status_code == 400


def test_post_contexts_invalid_name_returns_error_in_body(client: TestClient) -> None:
    response = client.post("/ui/contexts", data={"name": "NO"})

    assert 'class="error"' in response.text
    assert "at least" in response.text


def test_post_contexts_invalid_name_returns_form_fragment(client: TestClient) -> None:
    response = client.post("/ui/contexts", data={"name": "NO"})

    assert "text/html" in response.headers["content-type"]
    assert "form" in response.text.lower() or "input" in response.text.lower()


# --- GET /ui/_new-context-form ---


def test_get_new_context_form_returns_200(client: TestClient) -> None:
    response = client.get("/ui/_new-context-form")

    assert response.status_code == 200


def test_get_new_context_form_returns_html(client: TestClient) -> None:
    response = client.get("/ui/_new-context-form")

    assert "text/html" in response.headers["content-type"]


def test_get_new_context_form_contains_form(client: TestClient) -> None:
    response = client.get("/ui/_new-context-form")

    assert "<form" in response.text


def test_get_new_context_form_posts_to_correct_target(client: TestClient) -> None:
    response = client.get("/ui/_new-context-form")

    assert 'hx-post="/ui/contexts"' in response.text or 'action="/ui/contexts"' in response.text
