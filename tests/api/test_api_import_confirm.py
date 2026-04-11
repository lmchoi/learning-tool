from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.ingestion.store import ContextStore

_VALID_CHAT_RESPONSE = """\
## Goal
Learn Python async programming.

## Questions
### Coroutines
- What is a coroutine?
- How does await work?
### Event loop
- What does the event loop do?
- How do you run a coroutine?
"""


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient]:
    with (
        patch("learning_tool.api.main.SentenceTransformerEmbedder"),
        patch("learning_tool.api.main.AsyncAnthropic"),
        patch("learning_tool.api.main.genai"),
        patch("learning_tool.api.deps.SessionStore"),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        TestClient(app) as c,
    ):
        c.app.state.store_dir = tmp_path  # type: ignore[attr-defined]
        c.app.state.context_store = ContextStore(tmp_path)  # type: ignore[attr-defined]
        yield c


# --- POST /import ---


def test_post_import_returns_200(client: TestClient) -> None:
    response = client.post("/ui/python/import", data={"chat_response": _VALID_CHAT_RESPONSE})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_post_import_renders_review_screen(client: TestClient) -> None:
    response = client.post("/ui/python/import", data={"chat_response": _VALID_CHAT_RESPONSE})

    assert "review" in response.text.lower() or "Confirm import" in response.text


def test_post_import_shows_questions_as_editable_inputs(client: TestClient) -> None:
    response = client.post("/ui/python/import", data={"chat_response": _VALID_CHAT_RESPONSE})

    assert "What is a coroutine?" in response.text
    assert 'type="text"' in response.text


def test_post_import_groups_questions_by_focus_area(client: TestClient) -> None:
    response = client.post("/ui/python/import", data={"chat_response": _VALID_CHAT_RESPONSE})

    assert "Coroutines" in response.text
    assert "Event loop" in response.text


def test_post_import_embeds_goal_in_hidden_field(client: TestClient) -> None:
    response = client.post("/ui/python/import", data={"chat_response": _VALID_CHAT_RESPONSE})

    assert "Learn Python async programming" in response.text


def test_post_import_does_not_write_files(client: TestClient, tmp_path: Path) -> None:
    client.post("/ui/python/import", data={"chat_response": _VALID_CHAT_RESPONSE})

    assert not (tmp_path / "python" / "context.yaml").exists()
    assert not (tmp_path / "python" / "questions.yaml").exists()


def test_post_import_returns_422_for_invalid_response(client: TestClient) -> None:
    response = client.post("/ui/python/import", data={"chat_response": "not valid markup"})

    assert response.status_code == 422


# --- POST /confirm ---


def _confirm_payload(
    goal: str = "Learn Python async programming.",
    focus_areas: list[str] | None = None,
    questions_by_area: dict[str, list[str]] | None = None,
) -> dict[str, str | list[str]]:
    """Build a form payload matching what import_review.html submits.

    Uses dict-of-lists so TestClient sends multiple values for the same key.
    """
    if focus_areas is None:
        focus_areas = ["Coroutines", "Event loop"]
    if questions_by_area is None:
        questions_by_area = {
            "Coroutines": ["What is a coroutine?", "How does await work?"],
            "Event loop": ["What does the event loop do?", "How do you run a coroutine?"],
        }
    data: dict[str, str | list[str]] = {"goal": goal, "focus_area": list(focus_areas)}
    for fa in focus_areas:
        qs = questions_by_area.get(fa, [])
        data[f"question_{fa}"] = list(qs)
    return data


def test_post_confirm_returns_200(client: TestClient) -> None:
    response = client.post("/ui/python/confirm", data=_confirm_payload())

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_post_confirm_renders_result_screen(client: TestClient) -> None:
    response = client.post("/ui/python/confirm", data=_confirm_payload())

    assert "Context imported" in response.text or "Files written" in response.text


def test_post_confirm_writes_context_yaml(client: TestClient, tmp_path: Path) -> None:
    client.post("/ui/python/confirm", data=_confirm_payload())

    ctx_path = tmp_path / "python" / "context.yaml"
    assert ctx_path.exists()
    data = yaml.safe_load(ctx_path.read_text())
    assert data["goal"] == "Learn Python async programming."
    assert "Coroutines" in data["focus_areas"]
    assert "Event loop" in data["focus_areas"]


def test_post_confirm_writes_questions_yaml(client: TestClient, tmp_path: Path) -> None:
    client.post("/ui/python/confirm", data=_confirm_payload())

    q_path = tmp_path / "python" / "questions.yaml"
    assert q_path.exists()
    data = yaml.safe_load(q_path.read_text())
    assert any(entry["focus_area"] == "Coroutines" for entry in data)
    coroutines_entry = next(e for e in data if e["focus_area"] == "Coroutines")
    assert "What is a coroutine?" in coroutines_entry["questions"]
    assert "How does await work?" in coroutines_entry["questions"]


def test_post_confirm_with_removed_question_omits_it_from_files(
    client: TestClient, tmp_path: Path
) -> None:
    # Simulate user removing "How does await work?" before confirming
    data = _confirm_payload(
        questions_by_area={
            "Coroutines": ["What is a coroutine?"],  # one removed
            "Event loop": ["What does the event loop do?", "How do you run a coroutine?"],
        }
    )
    client.post("/ui/python/confirm", data=data)

    q_path = tmp_path / "python" / "questions.yaml"
    questions_data = yaml.safe_load(q_path.read_text())
    coroutines_entry = next(e for e in questions_data if e["focus_area"] == "Coroutines")
    assert "How does await work?" not in coroutines_entry["questions"]
    assert len(coroutines_entry["questions"]) == 1


def test_post_confirm_with_edited_question_writes_edited_text(
    client: TestClient, tmp_path: Path
) -> None:
    # Simulate user editing "What is a coroutine?" to "Explain a coroutine."
    data = _confirm_payload(
        questions_by_area={
            "Coroutines": ["Explain a coroutine.", "How does await work?"],
            "Event loop": ["What does the event loop do?", "How do you run a coroutine?"],
        }
    )
    client.post("/ui/python/confirm", data=data)

    q_path = tmp_path / "python" / "questions.yaml"
    questions_data = yaml.safe_load(q_path.read_text())
    coroutines_entry = next(e for e in questions_data if e["focus_area"] == "Coroutines")
    assert "Explain a coroutine." in coroutines_entry["questions"]
    assert "What is a coroutine?" not in coroutines_entry["questions"]


def test_post_confirm_returns_422_for_empty_goal(client: TestClient) -> None:
    response = client.post("/ui/python/confirm", data=_confirm_payload(goal=""))

    assert response.status_code == 422


def test_post_confirm_returns_422_when_all_questions_removed(client: TestClient) -> None:
    data = _confirm_payload(
        questions_by_area={"Coroutines": [], "Event loop": []},
    )
    response = client.post("/ui/python/confirm", data=data)

    assert response.status_code == 422


def test_post_confirm_skips_focus_area_with_all_questions_removed(
    client: TestClient, tmp_path: Path
) -> None:
    # Simulate user removing all questions from "Event loop"
    data = _confirm_payload(
        questions_by_area={
            "Coroutines": ["What is a coroutine?"],
            "Event loop": [],  # all removed
        }
    )
    client.post("/ui/python/confirm", data=data)

    ctx_path = tmp_path / "python" / "context.yaml"
    ctx_data = yaml.safe_load(ctx_path.read_text())
    assert "Event loop" not in ctx_data["focus_areas"]

    q_path = tmp_path / "python" / "questions.yaml"
    q_data = yaml.safe_load(q_path.read_text())
    assert not any(e["focus_area"] == "Event loop" for e in q_data)
