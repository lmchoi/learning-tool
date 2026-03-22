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


def test_record_stores_result_json(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    store.record(session_id, "Q?", "A.", 7, result_json='{"score": 7}')

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT result_json FROM attempts").fetchone()
    assert row[0] == '{"score": 7}'


def test_load_annotations_returns_joined_data(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    attempt_id = store.record(
        session_id, "Q?", "A.", 6, question_id="qid-1", result_json='{"score": 6}'
    )
    store.record_chunks(attempt_id, [("chunk a", 0.9), ("chunk b", 0.8)])
    store.record_annotation("qid-1", "evaluation", "down", comment="Off target")

    annotations = store.load_annotations()

    assert len(annotations) == 1
    ann = annotations[0]
    assert ann["question_text"] == "Q?"
    assert ann["answer_text"] == "A."
    assert ann["score"] == 6
    assert ann["result_json"] == '{"score": 6}'
    assert ann["target_type"] == "evaluation"
    assert ann["sentiment"] == "down"
    assert ann["comment"] == "Off target"
    assert ann["chunks"] == [("chunk a", 0.9), ("chunk b", 0.8)]
    assert ann["flagged_at"] is None


def test_load_annotations_filter_by_target_type(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    store.record(session_id, "Q1?", "A1.", 5, question_id="qid-1")
    store.record(session_id, "Q2?", "A2.", 7, question_id="qid-2")
    store.record_annotation("qid-1", "question", "down")
    store.record_annotation("qid-2", "evaluation", "down", comment="Bad eval")

    results = store.load_annotations(target_type="evaluation")
    assert len(results) == 1
    assert results[0]["target_type"] == "evaluation"


def test_load_annotations_filter_by_sentiment(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    store.record(session_id, "Q1?", "A1.", 5, question_id="qid-1")
    store.record(session_id, "Q2?", "A2.", 9, question_id="qid-2")
    store.record_annotation("qid-1", "question", "down")
    store.record_annotation("qid-2", "question", "up")

    results = store.load_annotations(sentiment="up")
    assert len(results) == 1
    assert results[0]["sentiment"] == "up"


def test_record_chunks_and_load_chunks(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    attempt_id = store.record(session_id, "Q?", "A.", 5)

    store.record_chunks(attempt_id, [("chunk one", 0.9), ("chunk two", 0.8), ("chunk three", 0.7)])

    loaded = store.load_chunks(attempt_id)
    assert loaded == [("chunk one", 0.9), ("chunk two", 0.8), ("chunk three", 0.7)]


def test_load_chunks_empty(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    attempt_id = store.record(session_id, "Q?", "A.", 5)

    assert store.load_chunks(attempt_id) == []


def test_record_chunks_isolated_per_attempt(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    session_id = store.start_session()
    attempt_a = store.record(session_id, "Q1?", "A1.", 5)
    attempt_b = store.record(session_id, "Q2?", "A2.", 7)

    store.record_chunks(attempt_a, [("chunk for a", 0.9)])
    store.record_chunks(attempt_b, [("chunk for b", 0.8)])

    assert store.load_chunks(attempt_a) == [("chunk for a", 0.9)]
    assert store.load_chunks(attempt_b) == [("chunk for b", 0.8)]


def test_record_annotation_evaluation_target_type(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()

    store.record_annotation("qid-eval", "evaluation", "down", comment="Feedback was wrong")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT target_type, sentiment, comment FROM annotations").fetchone()
    assert row[0] == "evaluation"
    assert row[1] == "down"
    assert row[2] == "Feedback was wrong"


def test_record_annotation_unique_per_question_and_target_type(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()

    store.record_annotation("qid-eval", "evaluation", "down", comment="First report")
    store.record_annotation("qid-eval", "evaluation", "down", comment="Updated report")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT comment FROM annotations").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Updated report"


def test_chunks_score_migration(tmp_path: Path) -> None:
    """Migration adds score column to existing chunks table that lacks it."""
    ctx_dir = tmp_path / "ctx"
    ctx_dir.mkdir()
    db_path = ctx_dir / "sessions.db"

    # Simulate a pre-migration DB: chunks table without score column
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            "CREATE TABLE sessions"
            " (session_id TEXT PRIMARY KEY, context TEXT NOT NULL, started_at TEXT NOT NULL);"
            "CREATE TABLE attempts"
            " (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,"
            " question_id TEXT, question_text TEXT NOT NULL, answer_text TEXT NOT NULL,"
            " score INTEGER NOT NULL, result_json TEXT, timestamp TEXT NOT NULL);"
            "CREATE TABLE chunks"
            " (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " attempt_id INTEGER NOT NULL, chunk_text TEXT NOT NULL);"
            "INSERT INTO sessions VALUES ('s1', 'ctx', '2024-01-01T00:00:00+00:00');"
            "INSERT INTO attempts"
            " VALUES (1, 's1', NULL, 'Q?', 'A.', 5, NULL, '2024-01-01T00:00:00+00:00');"
            "INSERT INTO chunks (attempt_id, chunk_text) VALUES (1, 'old chunk');"
        )

    # Opening SessionStore should run migration and add score column
    store = SessionStore(tmp_path, "ctx")

    # Migrated row has score = NULL
    loaded = store.load_chunks(1)
    assert loaded == [("old chunk", None)]

    # New chunks can be stored with scores
    session_id = store.start_session()
    attempt_id = store.record(session_id, "Q2?", "A2.", 7)
    store.record_chunks(attempt_id, [("new chunk", 0.85)])
    assert store.load_chunks(attempt_id) == [("new chunk", 0.85)]


def test_flag_annotation_sets_flagged_at(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()
    store.record_annotation("qid-1", "question", "down")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id, flagged_at FROM annotations").fetchone()
    annotation_id, flagged_at = row
    assert flagged_at is None

    store.flag_annotation(annotation_id)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT flagged_at FROM annotations WHERE id = ?", (annotation_id,)
        ).fetchone()
    assert row[0] is not None


def test_flag_annotation_does_not_affect_sentiment(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()
    store.record_annotation("qid-1", "question", "up")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        annotation_id = conn.execute("SELECT id FROM annotations").fetchone()[0]

    store.flag_annotation(annotation_id)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT sentiment FROM annotations WHERE id = ?", (annotation_id,)
        ).fetchone()
    assert row[0] == "up"


def test_load_annotations_filter_flagged(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()
    store.record_annotation("qid-1", "question", "down")
    store.record_annotation("qid-2", "question", "up")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        annotation_id = conn.execute(
            "SELECT id FROM annotations WHERE question_id = 'qid-1'"
        ).fetchone()[0]

    store.flag_annotation(annotation_id)

    flagged = store.load_annotations(flagged=True)
    assert len(flagged) == 1
    assert flagged[0]["question_id"] == "qid-1"
    assert flagged[0]["flagged_at"] is not None

    all_annotations = store.load_annotations()
    assert len(all_annotations) == 2


def test_load_annotations_flagged_and_sentiment_combined(tmp_path: Path) -> None:
    store = SessionStore(tmp_path, "ctx")
    store.start_session()
    store.record_annotation("qid-1", "question", "down")
    store.record_annotation("qid-2", "question", "up")
    store.record_annotation("qid-3", "question", "down")

    db_path = tmp_path / "ctx" / "sessions.db"
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, question_id FROM annotations WHERE question_id IN ('qid-1', 'qid-2')"
        ).fetchall()
    id_map = {qid: aid for aid, qid in rows}

    store.flag_annotation(id_map["qid-1"])  # flagged + down
    store.flag_annotation(id_map["qid-2"])  # flagged + up

    results = store.load_annotations(flagged=True, sentiment="down")
    assert len(results) == 1
    assert results[0]["question_id"] == "qid-1"
