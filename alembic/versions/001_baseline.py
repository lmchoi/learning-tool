"""baseline schema

Revision ID: c3f8a2d1e094
Revises:
Create Date: 2026-03-24

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f8a2d1e094"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            context    TEXT NOT NULL,
            started_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT NOT NULL REFERENCES sessions(session_id),
            question_id   TEXT,
            question_text TEXT NOT NULL,
            answer_text   TEXT NOT NULL,
            score         INTEGER NOT NULL,
            result_json   TEXT,
            timestamp     TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL REFERENCES attempts(id),
            chunk_text TEXT NOT NULL,
            score      REAL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS annotations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id  INTEGER REFERENCES attempts(id),
            question_id TEXT,
            target_type TEXT NOT NULL CHECK(target_type IN ('question', 'evaluation')),
            sentiment   TEXT NOT NULL CHECK(sentiment IN ('up', 'down')),
            comment     TEXT,
            created_at  TEXT NOT NULL,
            flagged_at  TEXT,
            UNIQUE(question_id, target_type)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS annotations")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS attempts")
    op.execute("DROP TABLE IF EXISTS sessions")
