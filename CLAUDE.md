# CLAUDE.md

## What This Is

A domain-agnostic personalised learning tool. The core never knows what is being
learned — it only knows: here is a knowledge base, here is a learner profile, here
is config. Generate questions, evaluate answers, ask follow-ups.

## Architecture Rules

- **Core must stay domain-agnostic.** If something is hardcoded to a specific context, it is wrong.
- **`contexts/` is gitignored entirely.** It contains personal learner data.
- **Async throughout.** This is both a design requirement and a learning objective.
  Use `asyncio.gather` for independent work, not sequential awaits.
- **Web UI is primary.** HTMX + FastAPI. No Gradio.
- **CLI is optional and secondary** — used only for context setup tasks.

## Stack

- FastAPI + HTMX for web
- RAG with numpy first, ChromaDB later — chunk, embed, cosine similarity (see docs/decisions/002)
- Faster-Whisper for local STT
- Claude API for question generation, evaluation, Socratic mode
- Railway for deployment

## Engineering Principles

Don't add something until there's a reason to — dependencies, abstractions,
infrastructure, features. See docs/conventions/003-engineering-principles.md.

Exception: decisions that are hard to reverse or would require restructuring later.
Ask — if we skip this now and need it later, how much does it cost to add?

## Adding Dependencies

Add runtime deps only when writing the code that needs them. Do not front-load.

## Git Workflow

- **Never commit directly to main.** Always create a feature branch first.
- Raise a PR for all changes, including setup/tooling work.
- Keep commits atomic — one logical change per commit. If unrelated files were touched, split into separate commits.
- Use `git reset --soft` for commit reorganisation, not file-by-file editing.
- Do not assume a branch is merged just because it's gone — squash merges don't appear in `git branch --merged`. Check PR status instead.
- Before any commit: run checks (see Running Checks below). Do not commit if anything fails.

## Scope

- Do not implement or add content beyond what was explicitly requested.
- During design or planning discussions, do not edit files unless asked to.

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

## Memory

Claude memory files are checked into `.claude/memory/`. On a new machine, symlink them into the project memory path:

```bash
ln -s $(pwd)/.claude/memory ~/.claude/projects/$(pwd | sed 's|/|-|g' | sed 's|^-||')/memory
```

## What to Read First

Read `something.md` for full project brief, architecture, data models, and build order.
