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
    question_id   TEXT,
    question_text TEXT NOT NULL,
    answer_text   TEXT NOT NULL,
    score         INTEGER NOT NULL,
    timestamp     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annotations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id  INTEGER REFERENCES attempts(id),
    question_id TEXT,
    target_type TEXT NOT NULL CHECK(target_type IN ('question', 'evaluation')),
    sentiment   TEXT NOT NULL CHECK(sentiment IN ('up', 'down')),
    comment     TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE(question_id, target_type)  -- one per question; INSERT OR REPLACE means last write wins
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
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        attempts_cols = {row[1] for row in conn.execute("PRAGMA table_info(attempts)").fetchall()}
        if "question_id" not in attempts_cols:
            conn.execute("ALTER TABLE attempts ADD COLUMN question_id TEXT")
        annotations_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(annotations)").fetchall()
        }
        if "question_id" not in annotations_cols:
            # Recreate annotations to change UNIQUE key from (attempt_id, target_type)
            # to (question_id, target_type) and make attempt_id nullable.
            # This drops existing annotation data — acceptable for dev, revisit before
            # any production deployment with real annotation history.
            conn.executescript(
                "DROP TABLE annotations;"
                "CREATE TABLE annotations ("
                "    id          INTEGER PRIMARY KEY AUTOINCREMENT,"
                "    attempt_id  INTEGER REFERENCES attempts(id),"
                "    question_id TEXT,"
                "    target_type TEXT NOT NULL CHECK(target_type IN ('question', 'evaluation')),"
                "    sentiment   TEXT NOT NULL CHECK(sentiment IN ('up', 'down')),"
                "    comment     TEXT,"
                "    created_at  TEXT NOT NULL,"
                "    UNIQUE(question_id, target_type)"
                ");"
            )

    def start_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        self._create_session(session_id, datetime.now(UTC).isoformat())
        return session_id

    def record(
        self,
        session_id: str,
        question_text: str,
        answer_text: str,
        score: int,
        question_id: str | None = None,
    ) -> int:
        """Record an attempt with the current timestamp. Returns the attempt id."""
        return self._add_attempt(
            QuestionAttempt(
                session_id=session_id,
                question_id=question_id,
                question_text=question_text,
                answer_text=answer_text,
                score=score,
                timestamp=datetime.now(UTC).isoformat(),
            )
        )

    def record_annotation(
        self,
        question_id: str,
        target_type: str,
        sentiment: str,
        comment: str | None = None,
    ) -> None:
        """Record a learner annotation (thumbs up/down) keyed by question_id."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT OR REPLACE INTO annotations"
                " (question_id, target_type, sentiment, comment, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (question_id, target_type, sentiment, comment, datetime.now(UTC).isoformat()),
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
                "INSERT INTO attempts"
                " (session_id, question_id, question_text, answer_text, score, timestamp)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    attempt.session_id,
                    attempt.question_id,
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
                    "SELECT session_id, question_id, question_text, answer_text, score, timestamp"
                    " FROM attempts WHERE session_id = ? ORDER BY id",
                    (session_id,),
                ).fetchall()
                attempts = [
                    QuestionAttempt(
                        session_id=r[0],
                        question_id=r[1],
                        question_text=r[2],
                        answer_text=r[3],
                        score=r[4],
                        timestamp=r[5],
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
