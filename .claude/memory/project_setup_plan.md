---
name: Project current state
description: Current build progress, open issues, and what's next
type: project
---

## What's built (as of 2026-03-19)

Core pipeline is working end-to-end via CLI:
- Ingestion — chunk, embed (all-MiniLM-L6-v2), store as numpy arrays
- Retrieval — cosine similarity over numpy
- Question generation — RAG + Claude, returns `Question` Pydantic model
- Answer evaluation — returns `EvaluationResult` (score, strengths, gaps, missing_points, suggested_addition, follow_up_question)
- `make practice` — interactive CLI loop: question → answer → evaluate → follow-up, Ctrl+C to exit

FastAPI skeleton in place:
- `api/main.py` — `GET /health` returns `{"status": "ok"}`
- `make serve` starts uvicorn with --reload

## Open issues (GitHub)

- **#32** — `GET /contexts/{context_name}/question?query=<topic>` — next to build
- **#33** — `POST /contexts/{context_name}/evaluate`
- **#34** — `POST /contexts/{context_name}/ingest` + `GET /contexts/`
- **#25** PR open — practice loop (feature/practice-loop) — pending merge
- **#36** PR open — healthcheck (feature/api-healthcheck) — pending merge

## What's next

Issue #32: `GET /contexts/{context_name}/question`
- Lifespan: init `SentenceTransformerEmbedder`, `ChunkStore`, `Retriever`, `AsyncAnthropic` once at startup on `app.state`
- Store dir from `STORE_DIR` env var, default `"contexts/store"`
- `experience_level` hardcoded to `"beginner"` (profile system is a future issue)
- 404 on unknown context (FileNotFoundError from store)
- Tests: 200 happy path + 404, patch `generate_question` and `Retriever`

After #32 + #33: HTMX frontend (separate issue to create)

## Key data models

```python
class Question(BaseModel):
    text: str

class EvaluationResult(BaseModel):
    score: Annotated[int, Field(ge=0, le=10)]
    strengths: list[str]
    gaps: list[str]
    missing_points: list[str]
    suggested_addition: str | None
    follow_up_question: str  # always present, used to drive practice loop
```

## Key paths

- `core/` — domain-agnostic logic
- `api/main.py` — FastAPI app
- `cli/main.py` — CLI (reference for how core pieces wire together)
- `contexts/store/` — gitignored, ingested context data lives here
- `tests/fakes.py` — FakeAnthropicClient for tests
