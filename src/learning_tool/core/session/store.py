import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config

from alembic import command
from learning_tool.core.session.models import QuestionAttempt, SessionRecord

_ALEMBIC_DIR = Path(__file__).resolve().parents[4] / "alembic"


class SessionStore:
    def __init__(self, base_dir: Path, context: str) -> None:
        ctx_dir = base_dir / context
        ctx_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = ctx_dir / "sessions.db"
        self._context = context
        self._init_db()

    def _init_db(self) -> None:
        cfg = Config()
        cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{self._db_path}")

        with sqlite3.connect(self._db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }

        if tables and "alembic_version" not in tables:
            # Existing DB previously managed by _migrate() — stamp at the last revision
            # that matches the pre-alembic schema (baseline + question_id index) so that
            # any migrations added after that point are applied by the upgrade below.
            command.stamp(cfg, "b4e7f91c2a83")

        command.upgrade(cfg, "head")

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
        score: int | None,
        question_id: str | None = None,
        result_json: str | None = None,
        focus_area: str | None = None,
    ) -> int:
        """Record an attempt with the current timestamp. Returns the attempt id."""
        timestamp = datetime.now(UTC).isoformat()
        self._ensure_session(session_id, timestamp)
        return self._add_attempt(
            QuestionAttempt(
                session_id=session_id,
                question_id=question_id,
                question_text=question_text,
                answer_text=answer_text,
                score=score,
                timestamp=timestamp,
                focus_area=focus_area,
            ),
            result_json=result_json,
        )

    def update_attempt_result(
        self,
        attempt_id: int,
        score: int,
        result_json: str | None = None,
    ) -> bool:
        """Update an attempt's score and result_json by its primary key. Returns True if updated."""
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "UPDATE attempts SET score = ?, result_json = ? WHERE id = ?",
                (score, result_json, attempt_id),
            )
            return cursor.rowcount > 0

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

    def flag_annotation(self, annotation_id: int) -> None:
        """Set flagged_at on an annotation to mark it for review."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "UPDATE annotations SET flagged_at = ? WHERE id = ?",
                (datetime.now(UTC).isoformat(), annotation_id),
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
        flagged: bool = False,
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
        if flagged:
            filters.append("a.flagged_at IS NOT NULL")
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        query = f"""
            SELECT
                a.id,
                a.question_id,
                a.target_type,
                a.sentiment,
                a.comment,
                a.created_at,
                a.flagged_at,
                att.id as attempt_id,
                att.question_text,
                att.answer_text,
                att.score,
                att.result_json
            FROM annotations a
            LEFT JOIN attempts att ON att.question_id = a.question_id
            {where}
            ORDER BY a.id DESC
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

            attempt_ids = [row["attempt_id"] for row in rows if row["attempt_id"] is not None]
            chunks_by_attempt: dict[int, list[tuple[str, float | None]]] = {}
            if attempt_ids:
                placeholders = ",".join("?" * len(attempt_ids))
                chunk_rows = conn.execute(
                    f"SELECT attempt_id, chunk_text, score FROM chunks"
                    f" WHERE attempt_id IN ({placeholders}) ORDER BY id",
                    attempt_ids,
                ).fetchall()
                for c in chunk_rows:
                    chunks_by_attempt.setdefault(c[0], []).append((c[1], c[2]))

            result = []
            for row in rows:
                aid = row["attempt_id"]
                result.append(
                    {
                        "id": row["id"],
                        "question_id": row["question_id"],
                        "target_type": row["target_type"],
                        "sentiment": row["sentiment"],
                        "comment": row["comment"],
                        "created_at": row["created_at"],
                        "flagged_at": row["flagged_at"],
                        "question_text": row["question_text"],
                        "answer_text": row["answer_text"],
                        "score": row["score"],
                        "result_json": row["result_json"],
                        "chunks": chunks_by_attempt.get(aid, []) if aid is not None else [],
                    }
                )
            return result

    def load_annotation(self, annotation_id: int) -> dict[str, object] | None:
        """Return a single annotation by id, or None if not found."""
        results = self.load_annotations(annotation_id=annotation_id)
        return results[0] if results else None

    def _create_session(self, session_id: str, started_at: str) -> None:
        # Intentionally uses INSERT (not INSERT OR IGNORE) — duplicate explicit
        # start_session() calls should raise rather than silently succeed.
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, context, started_at) VALUES (?, ?, ?)",
                (session_id, self._context, started_at),
            )

    def _ensure_session(self, session_id: str, started_at: str) -> None:
        """Insert a session row if one does not already exist (no-op on conflict).

        Used by record() to handle the MCP path, where the adapter generates a
        session_id at startup without calling start_session(). For these sessions
        started_at will equal the timestamp of the first recorded attempt.
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id, context, started_at) VALUES (?, ?, ?)",
                (session_id, self._context, started_at),
            )

    def _add_attempt(self, attempt: QuestionAttempt, result_json: str | None = None) -> int:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO attempts"
                " (session_id, question_id, question_text, answer_text,"
                " score, result_json, timestamp, focus_area)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt.session_id,
                    attempt.question_id,
                    attempt.question_text,
                    attempt.answer_text,
                    attempt.score,
                    result_json,
                    attempt.timestamp,
                    attempt.focus_area,
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]  # always set after INSERT on autoincrement table

    def load_session(self, session_id: str) -> SessionRecord | None:
        """Return a single session by session_id, or None if not found."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT session_id, context, started_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            attempt_rows = conn.execute(
                "SELECT id, session_id, question_id, question_text, answer_text,"
                " score, timestamp, result_json, focus_area"
                " FROM attempts WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            attempts = [
                QuestionAttempt(
                    session_id=r["session_id"],
                    question_id=r["question_id"],
                    question_text=r["question_text"],
                    answer_text=r["answer_text"],
                    score=r["score"],
                    timestamp=r["timestamp"],
                    result_json=r["result_json"],
                    attempt_id=r["id"],
                    focus_area=r["focus_area"],
                )
                for r in attempt_rows
            ]
            return SessionRecord(
                session_id=row["session_id"],
                context=row["context"],
                started_at=row["started_at"],
                attempts=attempts,
            )

    def load_sessions(self) -> list[SessionRecord]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT session_id, context, started_at FROM sessions ORDER BY started_at"
            ).fetchall()
            records = []
            for row in rows:
                attempt_rows = conn.execute(
                    "SELECT id, session_id, question_id, question_text, answer_text,"
                    " score, timestamp, result_json, focus_area"
                    " FROM attempts WHERE session_id = ? ORDER BY id",
                    (row["session_id"],),
                ).fetchall()
                attempts = [
                    QuestionAttempt(
                        session_id=r["session_id"],
                        question_id=r["question_id"],
                        question_text=r["question_text"],
                        answer_text=r["answer_text"],
                        score=r["score"],
                        timestamp=r["timestamp"],
                        result_json=r["result_json"],
                        attempt_id=r["id"],
                        focus_area=r["focus_area"],
                    )
                    for r in attempt_rows
                ]
                records.append(
                    SessionRecord(
                        session_id=row["session_id"],
                        context=row["context"],
                        started_at=row["started_at"],
                        attempts=attempts,
                    )
                )
            return records
