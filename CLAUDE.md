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
- Claude API for question generation and evaluation (server-side fallback; primary path moves generation/evaluation to the user's own LLM chat via MCP)
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

- `src/learning_tool/core/` — the tool, domain agnostic
- `src/learning_tool/core/settings.py` — single source of truth for env var config (STORE_DIR etc); both API and CLI import from here
- `src/learning_tool/core/<domain>/store.py` — storage for that domain (follows `core/ingestion/store.py` precedent; storage lives in the domain layer, not a separate infrastructure layer — see ADR 010)
- `contexts/` — pluggable learning contexts, gitignored

## GitHub Milestones

Issues are organised into milestones. When creating a new issue, assign it to the most relevant one.

| Milestone | What belongs there |
|---|---|
| **Learner Progress** | Session history, weak area surfacing, multi-learner support — anything tracking how the learner improves over time |
| **Question Generation** | Question generation, retrieval strategy, question bank, Socratic follow-up, user-entered questions |
| **Observability** | LLM call logging, Langfuse integration, annotation and feedback collection on questions/evaluations |
| **Model Control** | Provider abstraction, per-task model defaults, model visibility in UI, user-selectable models |
| **Ingestion** | Ingestion pipeline, source management, chunking, embedding |
| **Chat Integration** | Import context from AI chat sessions and export practice results back |
| **In-chat Practice** | MCP server and channel-agnostic adapter layer — practice loop runs in Claude Desktop, tool handles storage and progress |

Issues that don't fit a milestone (housekeeping, bug fixes, warnings) can be left unassigned.

## Memory

Claude memory files are checked into `.claude/memory/`. On a new machine, symlink them into the project memory path:

```bash
ln -s $(pwd)/.claude/memory ~/.claude/projects/$(pwd | sed 's|/|-|g' | sed 's|^-||')/memory
```

## What to Read First

Read `docs/design/` for current design thinking and architectural decisions.
