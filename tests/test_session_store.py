from pathlib import Path

from core.session.models import QuestionAttempt
from core.session.store import SessionStore


def test_create_and_load_session(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.create_session("s1", "2026-03-21T09:00:00")

    sessions = store.load_sessions()

    assert len(sessions) == 1
    assert sessions[0].session_id == "s1"
    assert sessions[0].context == "ctx"
    assert sessions[0].started_at == "2026-03-21T09:00:00"
    assert sessions[0].attempts == []


def test_add_attempt_round_trip(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.create_session("s1", "2026-03-21T09:00:00")
    attempt = QuestionAttempt(
        session_id="s1",
        question_text="What is X?",
        answer_text="It is Y.",
        score=7,
        timestamp="2026-03-21T09:01:00",
    )
    store.add_attempt(attempt)

    sessions = store.load_sessions()

    assert len(sessions[0].attempts) == 1
    loaded = sessions[0].attempts[0]
    assert loaded.question_text == "What is X?"
    assert loaded.answer_text == "It is Y."
    assert loaded.score == 7
    assert loaded.timestamp == "2026-03-21T09:01:00"


def test_multiple_attempts_ordered(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.create_session("s1", "2026-03-21T09:00:00")
    for i, q in enumerate(["Q1", "Q2", "Q3"]):
        store.add_attempt(
            QuestionAttempt(
                session_id="s1",
                question_text=q,
                answer_text=f"Answer {i}",
                score=i + 5,
                timestamp=f"2026-03-21T09:0{i}:00",
            )
        )

    sessions = store.load_sessions()
    texts = [a.question_text for a in sessions[0].attempts]
    assert texts == ["Q1", "Q2", "Q3"]


def test_db_created_in_context_dir(tmp_path: Path) -> None:
    SessionStore(tmp_path, "my-context")
    assert (tmp_path / "my-context" / "sessions.db").exists()


def test_different_contexts_isolated(tmp_path: Path) -> None:
    store_a = SessionStore(tmp_path, "ctx-a")
    store_b = SessionStore(tmp_path, "ctx-b")
    store_a.create_session("s1", "2026-03-21T09:00:00")

    assert store_b.load_sessions() == []
    assert len(store_a.load_sessions()) == 1
