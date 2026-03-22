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
    result_json   TEXT,
    timestamp     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id),
    chunk_text TEXT NOT NULL,
    score      REAL
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
        if "result_json" not in attempts_cols:
            conn.execute("ALTER TABLE attempts ADD COLUMN result_json TEXT")
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "chunks" not in tables:
            conn.execute(
                "CREATE TABLE chunks ("
                "    id         INTEGER PRIMARY KEY AUTOINCREMENT,"
                "    attempt_id INTEGER NOT NULL REFERENCES attempts(id),"
                "    chunk_text TEXT NOT NULL,"
                "    score      REAL"
                ")"
            )
        chunks_cols = {row[1] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
        if "score" not in chunks_cols:
            conn.execute("ALTER TABLE chunks ADD COLUMN score REAL")
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
        result_json: str | None = None,
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
            ),
            result_json=result_json,
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

    def record_chunks(self, attempt_id: int, chunks: list[tuple[str, float]]) -> None:
        """Persist the retrieved chunks (text + similarity score) associated with an attempt."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executemany(
                "INSERT INTO chunks (attempt_id, chunk_text, score) VALUES (?, ?, ?)",
                [(attempt_id, text, score) for text, score in chunks],
            )

    def load_chunks(self, attempt_id: int) -> list[tuple[str, float | None]]:
        """Return the chunks stored for an attempt, in insertion order."""
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT chunk_text, score FROM chunks WHERE attempt_id = ? ORDER BY id",
                (attempt_id,),
            ).fetchall()
            return [(row[0], row[1]) for row in rows]

    def load_annotations(
        self,
        target_type: str | None = None,
        sentiment: str | None = None,
        annotation_id: int | None = None,
    ) -> list[dict[str, object]]:
        """Return annotations joined with attempt context, newest first."""
        filters = []
        params: list[object] = []
        if annotation_id is not None:
            filters.append("a.id = ?")
            params.append(annotation_id)
        if target_type is not None:
            filters.append("a.target_type = ?")
            params.append(target_type)
        if sentiment is not None:
            filters.append("a.sentiment = ?")
            params.append(sentiment)
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        query = f"""
            SELECT
                a.id,
                a.question_id,
                a.target_type,
                a.sentiment,
                a.comment,
                a.created_at,
                att.id as attempt_id,
                att.question_text,
                att.answer_text,
                att.score,
                att.result_json
            FROM annotations a
            LEFT JOIN attempts att ON (
                (a.question_id IS NOT NULL AND att.question_id = a.question_id)
                OR (a.question_id IS NULL AND a.attempt_id IS NOT NULL AND att.id = a.attempt_id)
            )
            {where}
            ORDER BY a.id DESC
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            result = []
            for row in rows:
                chunks: list[tuple[str, float | None]] = []
                if row["attempt_id"] is not None:
                    chunk_rows = conn.execute(
                        "SELECT chunk_text, score FROM chunks WHERE attempt_id = ? ORDER BY id",
                        (row["attempt_id"],),
                    ).fetchall()
                    chunks = [(c[0], c[1]) for c in chunk_rows]
                result.append(
                    {
                        "id": row["id"],
                        "question_id": row["question_id"],
                        "target_type": row["target_type"],
                        "sentiment": row["sentiment"],
                        "comment": row["comment"],
                        "created_at": row["created_at"],
                        "question_text": row["question_text"],
                        "answer_text": row["answer_text"],
                        "score": row["score"],
                        "result_json": row["result_json"],
                        "chunks": chunks,
                    }
                )
            return result

    def load_annotation(self, annotation_id: int) -> dict[str, object] | None:
        """Return a single annotation by id, or None if not found."""
        results = self.load_annotations(annotation_id=annotation_id)
        return results[0] if results else None

    def _create_session(self, session_id: str, started_at: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, context, started_at) VALUES (?, ?, ?)",
                (session_id, self._context, started_at),
            )

    def _add_attempt(self, attempt: QuestionAttempt, result_json: str | None = None) -> int:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO attempts"
                " (session_id, question_id, question_text, answer_text,"
                " score, result_json, timestamp)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt.session_id,
                    attempt.question_id,
                    attempt.question_text,
                    attempt.answer_text,
                    attempt.score,
                    result_json,
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
