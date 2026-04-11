"""make attempts.score nullable

Revision ID: f4a9c2e7b813
Revises: d9c3a7b15e62
Create Date: 2026-04-11

"""

from collections.abc import Sequence

import sqlalchemy

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a9c2e7b813"
down_revision: str | None = "d9c3a7b15e62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    col_info = {
        row[1]: row[3]
        for row in bind.execute(sqlalchemy.text("PRAGMA table_info(attempts)")).fetchall()
    }
    # notnull=1 means NOT NULL constraint; skip if already nullable
    if col_info.get("score") == 1:
        with op.batch_alter_table("attempts") as batch_op:
            batch_op.alter_column("score", existing_type=sqlalchemy.Integer(), nullable=True)


def downgrade() -> None:
    # Reverting to NOT NULL would fail for rows with score=NULL; skip.
    pass
