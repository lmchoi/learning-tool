import sqlite3
from pathlib import Path

import pytest

from core.session.store import SessionStore


def test_start_session_returns_id_and_persists(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()

    sessions = store.load_sessions()

    assert len(sessions) == 1
    assert sessions[0].session_id == session_id
    assert sessions[0].context == "ctx"
    assert sessions[0].attempts == []


def test_record_round_trip(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    store.record(session_id, "What is X?", "It is Y.", 7)

    sessions = store.load_sessions()

    assert len(sessions[0].attempts) == 1
    loaded = sessions[0].attempts[0]
    assert loaded.question_text == "What is X?"
    assert loaded.answer_text == "It is Y."
    assert loaded.score == 7
    assert loaded.timestamp  # ISO 8601 string, just check it's set


def test_multiple_attempts_ordered(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    for i, q in enumerate(["Q1", "Q2", "Q3"]):
        store.record(session_id, q, f"Answer {i}", i + 5)

    sessions = store.load_sessions()
    texts = [a.question_text for a in sessions[0].attempts]
    assert texts == ["Q1", "Q2", "Q3"]


def test_db_created_in_context_dir(tmp_path: Path) -> None:
    SessionStore(tmp_path, "my-context")
    assert (tmp_path / "my-context" / "sessions.db").exists()


def test_different_contexts_isolated(tmp_path: Path) -> None:
    store_a = SessionStore(tmp_path, "ctx-a")
    store_b = SessionStore(tmp_path, "ctx-b")
    store_a.start_session()

    assert store_b.load_sessions() == []
    assert len(store_a.load_sessions()) == 1


def test_record_returns_attempt_id(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    attempt_id = store.record(session_id, "Q?", "A.", 5)
    assert isinstance(attempt_id, int)
    assert attempt_id >= 1


def test_record_stores_question_id(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    store.record(session_id, "Q?", "A.", 5, question_id="test-qid")

    sessions = store.load_sessions()
    assert sessions[0].attempts[0].question_id == "test-qid"


def test_record_annotation_sentiment_only(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()

    store.record_annotation("test-qid", "question", "up")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT question_id, target_type, sentiment, comment, created_at FROM annotations"
        ).fetchone()
    assert row[0] == "test-qid"
    assert row[1] == "question"
    assert row[2] == "up"
    assert row[3] is None
    assert row[4]  # created_at set


def test_record_annotation_with_comment(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()

    store.record_annotation("test-qid", "question", "down", comment="Confusing wording")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT comment FROM annotations").fetchone()
    assert row[0] == "Confusing wording"


def test_record_annotation_invalid_sentiment(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()

    with pytest.raises(sqlite3.IntegrityError):
        store.record_annotation("test-qid", "question", "meh")


def test_record_annotation_invalid_target_type(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()

    with pytest.raises(sqlite3.IntegrityError):
        store.record_annotation("test-qid", "banana", "up")
