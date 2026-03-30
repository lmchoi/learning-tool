"""add focus_area column to attempts

Revision ID: d9c3a7b15e62
Revises: b4e7f91c2a83
Create Date: 2026-03-29

"""

from collections.abc import Sequence

import sqlalchemy

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9c3a7b15e62"
down_revision: str | None = "b4e7f91c2a83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Guard against legacy DBs that were stamped at head before this migration was
    # added — they won't have run the ALTER TABLE but would already be at head.
    bind = op.get_bind()
    cols = {
        row[1] for row in bind.execute(sqlalchemy.text("PRAGMA table_info(attempts)")).fetchall()
    }
    if "focus_area" not in cols:
        op.execute("ALTER TABLE attempts ADD COLUMN focus_area TEXT")


def downgrade() -> None:
    # SQLite ALTER TABLE DROP COLUMN is unsupported in the versions used here.
    pass
