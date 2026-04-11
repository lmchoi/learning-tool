from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from learning_tool.api.main import app
from learning_tool.core.session.store import SessionStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app.state.store_dir = tmp_path
    app.state.session_stores = {}
    app.state.bank_stores = {}
    return TestClient(app)


def test_post_capture_paste_back_success(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "my-ctx").mkdir()
    store = SessionStore(tmp_path, "my-ctx")
    sid = store.start_session()
    store.record(sid, "Q1", "A1", 0, question_id="qid-1")

    # Load session to get the real attempt_id
    session = store.load_session(sid)
    assert session is not None
    aid = session.attempts[0].attempt_id

    evaluation_text = f"""
```json
{{
  "question_id": "qid-1",
  "attempt_id": {aid},
  "score": 9,
  "strengths": ["Excellent"],
  "gaps": [],
  "missing_points": [],
  "suggested_addition": null,
  "follow_up_question": "Next?"
}}
```
"""
    resp = client.post(
        "/ui/my-ctx/capture/paste-back",
        data={"session_id": sid, "evaluation_text": evaluation_text},
        follow_redirects=False,
    )

    assert resp.status_code == 303
    assert "/ui/my-ctx/history?matched=1" in resp.headers["location"]

    session = store.load_session(sid)
    assert session is not None
    assert session.attempts[0].score == 9


def test_post_capture_paste_back_unmatched(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "my-ctx").mkdir()
    store = SessionStore(tmp_path, "my-ctx")
    sid = store.start_session()
    store.record(sid, "Q1", "A1", 0, question_id="qid-1")

    evaluation_text = """
```json
{
  "question_id": "q1",
  "attempt_id": 9999,
  "score": 5,
  "strengths": [],
  "gaps": [],
  "missing_points": [],
  "suggested_addition": null,
  "follow_up_question": "..."
}
```
"""
    resp = client.post(
        "/ui/my-ctx/capture/paste-back",
        data={"session_id": sid, "evaluation_text": evaluation_text},
        follow_redirects=False,
    )

    assert resp.status_code == 303
    assert "matched=0" in resp.headers["location"]
    assert "unmatched=9999" in resp.headers["location"]
