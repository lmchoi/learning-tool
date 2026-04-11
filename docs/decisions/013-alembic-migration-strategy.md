# ADR 013 — Alembic for SQLite schema migrations

## Status
Accepted

## Context
`SessionStore` started with a hand-rolled `_migrate()` method that added columns and
recreated tables inline via `PRAGMA table_info` checks. Every new schema change added
more conditionals — it was already dropping and recreating the `annotations` table on
migration. This approach doesn't scale and leaves no audit trail of what changed when.

## Decision
Use Alembic with raw SQL migrations (`op.execute()`). No SQLAlchemy ORM required —
Alembic is used purely as a migration runner.

## Why Alembic over alternatives
- **yoyo-migrations** — lightly maintained, thin docs
- **Hand-rolled** — already showing strain; no version tracking, no standard tooling
- **Alembic** — Python ecosystem standard, solid docs, clean path to SQLAlchemy ORM if
  ever needed

## Migration strategy for existing DBs
Existing databases were already fully migrated by `_migrate()`. On startup, if a DB
has tables but no `alembic_version` table, it is stamped at `head` — Alembic records
the current revision without re-running the baseline migration. Future migrations then
apply on top normally.

## When migrations run
Lazily — on the first request that touches a given context. Each context has its own
SQLite file (`{store_dir}/{context}/sessions.db`), so there is no single "migrate all"
command. To trigger migration for a specific context without a real request:

```bash
uv run python -c "
from learning_tool.core.session.store import SessionStore
from learning_tool.core.settings import STORE_DIR
SessionStore(STORE_DIR, '<context>')
"
```

Eager startup migration was considered but rejected: it would require iterating all
context directories at startup, and a failure would block all contexts rather than just
the affected one. Lazy init fails at the point of use, which is acceptable for a
single-user tool.

## Trade-offs
- Migration failures surface on first use, not at startup
- Alembic adds `sqlalchemy` as a transitive dependency (no ORM use, just connection layer)
- Each new schema change requires a migration file — more ceremony than `ALTER TABLE` inline

## Revisit if
The tool becomes multi-context or multi-user in a way that makes per-request migration
overhead significant, or if a proper deployment pipeline is introduced that can run
migrations as a pre-start step.
