# CLAUDE.md

## What This Is

A domain-agnostic personalised learning tool. The core never knows what is being
learned — it only knows: here is a knowledge base, here is a learner profile, here
is config. Generate questions, evaluate answers, ask follow-ups.

## Architecture Rules

- **Core must stay domain-agnostic.** If something is hardcoded to a specific context
  (e.g. `anthropic-fde`), it is wrong.
- **`contexts/` is gitignored entirely.** It contains personal learner data.
- **Async throughout.** This is both a design requirement and a learning objective.
  Use `asyncio.gather` for independent work, not sequential awaits.
- **Web UI is primary.** HTMX + FastAPI. No Gradio.
- **CLI is optional and secondary** — used only for context setup tasks.

## Stack

- FastAPI + HTMX for web
- ChromaDB for local vector store (`data/chroma/` — gitignored)
- sentence-transformers for embeddings
- Faster-Whisper for local STT
- Claude API for question generation, evaluation, Socratic mode
- Railway for deployment

## Adding Dependencies

Add runtime deps only when writing the code that needs them. Do not front-load.

## Running Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

## Key Paths

- `core/` — the tool, domain agnostic
- `contexts/` — pluggable learning contexts, gitignored
- `data/chroma/` — local vector store, gitignored

## What to Read First

Read `something.md` for full project brief, architecture, data models, and build order.
