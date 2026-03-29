# Schema Reference

> Update this doc when changing table definitions. For `sessions.db`, schema changes go via Alembic — see `alembic/versions/`.

The tool uses two SQLite databases per context, stored under `STORE_DIR/<context>/`.
The ingestion layer uses flat files (not SQLite) and is documented separately below.

---

## sessions.db

Managed by Alembic. The migration history lives in `alembic/versions/`.

### sessions

One row per practice session. Created when a learner starts a new session.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `session_id` | TEXT | NOT NULL | UUID, primary key |
| `context` | TEXT | NOT NULL | Name of the learning context (e.g. `"aws-saa"`) |
| `started_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |

### attempts

One row per question–answer pair within a session.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | NOT NULL | Auto-increment primary key |
| `session_id` | TEXT | NOT NULL | FK → `sessions.session_id` |
| `question_id` | TEXT | NULL | UUID linking back to `bank_questions.id`; NULL for ad-hoc questions not drawn from the bank |
| `question_text` | TEXT | NOT NULL | Full text of the question as shown to the learner |
| `answer_text` | TEXT | NOT NULL | Full text of the learner's answer |
| `score` | INTEGER | NOT NULL | Evaluation score 0–10; `0` is used as a deferred-evaluation placeholder in capture-mode sessions (see `POST /ui/{context}/capture`) |
| `result_json` | TEXT | NULL | JSON-serialised `EvaluationResult` (strengths, gaps, follow-up, etc.); NULL if evaluation was not run or not persisted |
| `timestamp` | TEXT | NOT NULL | ISO 8601 UTC timestamp of the attempt |

Index: `idx_attempts_question_id` on `attempts(question_id)` (added in migration `002`).

### chunks

RAG chunks retrieved to support a specific attempt. One row per chunk.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | NOT NULL | Auto-increment primary key |
| `attempt_id` | INTEGER | NOT NULL | FK → `attempts.id` |
| `chunk_text` | TEXT | NOT NULL | Raw text of the retrieved chunk |
| `score` | REAL | NULL | Cosine similarity score (0–1); NULL only if score was not available at insert time |

### annotations

Learner feedback (thumbs up / thumbs down) on a question or its evaluation.
One row per `(question_id, target_type)` pair — the `UNIQUE` constraint means a second
annotation replaces the first (`INSERT OR REPLACE`).

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | INTEGER | NOT NULL | Auto-increment primary key |
| `attempt_id` | INTEGER | NULL | FK → `attempts.id`; defined but currently unused — `record_annotation()` does not populate this column |
| `question_id` | TEXT | NULL | UUID matching `attempts.question_id` |
| `target_type` | TEXT | NOT NULL | `'question'` or `'evaluation'` (CHECK constraint) |
| `sentiment` | TEXT | NOT NULL | `'up'` or `'down'` (CHECK constraint) |
| `comment` | TEXT | NULL | Optional free-text note from the learner |
| `created_at` | TEXT | NOT NULL | ISO 8601 UTC timestamp |
| `flagged_at` | TEXT | NULL | ISO 8601 UTC timestamp set when an admin flags the annotation for review; NULL if not flagged |

Unique constraint: `(question_id, target_type)`.

### Relationships

```
sessions ──< attempts ──< chunks
                │
                └──< annotations (via question_id)
```

---

## bank.db

Managed directly (no Alembic). Schema is applied with `CREATE TABLE IF NOT EXISTS` on
every startup via `QuestionBankStore._init_db()`.

### bank_questions

The question bank: pre-authored questions grouped by focus area.

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | TEXT | NOT NULL | 12-character hex digest (SHA-256 of `focus_area + "\n" + question`), primary key |
| `focus_area` | TEXT | NOT NULL | Focus area label (e.g. `"IAM"`) |
| `question` | TEXT | NOT NULL | Full text of the question |

Inserts use `INSERT OR IGNORE` so re-importing the same question is a no-op.
The `id` is deterministic: same focus area + question always produces the same id.

---

## Flat-file stores (no SQLite)

All flat files live under `STORE_DIR/<context>/` alongside the SQLite databases.

### Ingestion layer (`ContextStore` / `ChunkStore`)

| File | Format | Contents |
|---|---|---|
| `<context>/context.yaml` | YAML | `ContextMetadata` (goal, focus_areas list) |
| `<context>/chunks.json` | JSON | List of text chunks produced by the ingestion pipeline |
| `<context>/embeddings.npy` | NumPy binary | Float32 embedding matrix, one row per chunk |

### Import layer (`POST /confirm`)

| File | Format | Contents |
|---|---|---|
| `<context>/questions.yaml` | YAML | Raw question list as imported/confirmed via the import flow; source of truth for `bank.db` |

Written by `POST /confirm` in `api/main.py`, not by the ingestion layer.
