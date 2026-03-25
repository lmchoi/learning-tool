"""add index on attempts.question_id

Revision ID: b4e7f91c2a83
Revises: c3f8a2d1e094
Create Date: 2026-03-25

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e7f91c2a83"
down_revision: str | None = "c3f8a2d1e094"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_attempts_question_id ON attempts(question_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_attempts_question_id")
