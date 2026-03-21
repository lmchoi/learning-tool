import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from core.session.models import QuestionAttempt, SessionRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    context    TEXT NOT NULL,
    started_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(session_id),
    question_text TEXT NOT NULL,
    answer_text   TEXT NOT NULL,
    score         INTEGER NOT NULL,
    timestamp     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annotations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id  INTEGER NOT NULL REFERENCES attempts(id),
    target_type TEXT NOT NULL CHECK(target_type IN ('question', 'evaluation')),
    sentiment   TEXT NOT NULL CHECK(sentiment IN ('up', 'down')),
    comment     TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE(attempt_id, target_type)  -- one per attempt; INSERT OR REPLACE means last write wins
);
"""


class SessionStore:
    def __init__(self, base_dir: Path, context: str) -> None:
        ctx_dir = base_dir / context
        ctx_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = ctx_dir / "sessions.db"
        self._context = context
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript(_SCHEMA)

    def start_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        self._create_session(session_id, datetime.now(UTC).isoformat())
        return session_id

    def record(self, session_id: str, question_text: str, answer_text: str, score: int) -> int:
        """Record an attempt with the current timestamp. Returns the attempt id."""
        return self._add_attempt(
            QuestionAttempt(
                session_id=session_id,
                question_text=question_text,
                answer_text=answer_text,
                score=score,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    def record_annotation(
        self,
        attempt_id: int,
        target_type: str,
        sentiment: str,
        comment: str | None = None,
    ) -> None:
        """Record a learner annotation (thumbs up/down) on an attempt."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT OR REPLACE INTO annotations"
                " (attempt_id, target_type, sentiment, comment, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (attempt_id, target_type, sentiment, comment, datetime.now(UTC).isoformat()),
            )

    def _create_session(self, session_id: str, started_at: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, context, started_at) VALUES (?, ?, ?)",
                (session_id, self._context, started_at),
            )

    def _add_attempt(self, attempt: QuestionAttempt) -> int:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO attempts (session_id, question_text, answer_text, score, timestamp)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    attempt.session_id,
                    attempt.question_text,
                    attempt.answer_text,
                    attempt.score,
                    attempt.timestamp,
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]  # always set after INSERT on autoincrement table

    def load_sessions(self) -> list[SessionRecord]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT session_id, context, started_at FROM sessions ORDER BY started_at"
            ).fetchall()
            records = []
            for session_id, context, started_at in rows:
                attempt_rows = conn.execute(
                    "SELECT session_id, question_text, answer_text, score, timestamp"
                    " FROM attempts WHERE session_id = ? ORDER BY id",
                    (session_id,),
                ).fetchall()
                attempts = [
                    QuestionAttempt(
                        session_id=r[0],
                        question_text=r[1],
                        answer_text=r[2],
                        score=r[3],
                        timestamp=r[4],
                    )
                    for r in attempt_rows
                ]
                records.append(
                    SessionRecord(
                        session_id=session_id,
                        context=context,
                        started_at=started_at,
                        attempts=attempts,
                    )
                )
            return records
