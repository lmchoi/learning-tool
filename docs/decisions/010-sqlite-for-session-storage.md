# ADR 010 — SQLite for session storage

## Status
Accepted

## Context
Issue #60 introduces session tracking — recording which questions were asked and
what scores were given — so that future sessions can surface weak areas (issue #28).

Two options were considered for persisting this data:

1. **JSON files** — one file per session, stored under `{store_dir}/{context}/sessions/`
2. **SQLite** — one database per context, stored at `{store_dir}/{context}/sessions.db`

## Decision
Use SQLite.

## Why not JSON files
JSON files fit the existing pattern (the chunk store already writes files under
`contexts/store/{context}/`), but issue #28 will need to query across all sessions
to find weak questions. That means reading every session file into memory and
filtering in Python — workable, but the wrong tool for the job.

## Why SQLite
- The query pattern for #28 is a natural SQL aggregate:
  `SELECT question_text, AVG(score) FROM attempts GROUP BY question_text`
- stdlib (`sqlite3`) — no new dependency
- Single file per context, simpler to manage than a directory of JSONs
- Still just a file — portable, no server, fits the single-user deployment model

## Trade-offs
- Schema migrations needed if the data model changes (minor for a single-user tool)
- Less transparent than JSON — can't just open a file and read it
- Slightly more setup than JSON serialisation

## Module placement
`SessionStore` lives in `core/session/store.py`, following the precedent set by
`core/ingestion/store.py` (`ChunkStore`). Storage is treated as part of the domain
layer, not a separate infrastructure layer.

Revisit this if `core/` grows unwieldy or a second storage backend (e.g. remote sync)
is introduced — at that point a clean infrastructure boundary would be worth the
refactor cost.

## Revisit if
The tool becomes multi-user or multi-process, at which point SQLite's concurrency
limits (single writer) would matter. For a single-user local tool this is not a concern.
