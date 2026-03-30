# learning-tool

A domain-agnostic personalised learning tool. The tool doesn't know what you're
learning — you plug in a context (knowledge base + config) and it generates
questions, evaluates answers, and tracks your progress over time.

## How it's built

This is a learning-by-building project. Sometimes the more complex approach is
taken — not because it's needed, but because understanding it is the point.
The `docs/` directory captures architectural decisions, engineering conventions,
and concepts encountered along the way.

### Capturing learnings as you build

`docs/learnings/` holds reference notes — concepts encountered while building,
with code examples. `contexts/user/` holds a learner profile — what you know
and don't yet, which drives question difficulty and how explanations are pitched.

Run `/update-notes` at the end of a Claude Code session to keep both up to date.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

Copy `.env.example` to `.env` and fill in your API keys, or put them in `~/.secrets/.env`.

## Usage

There are two ways to practise: the **web UI** and **Claude Desktop via MCP**.
Both read from and write to the same session store.

### Web UI

Start the server:

```bash
make serve
```

Then open `http://localhost:8000`.

**Flow:**

1. **Create a context** — go to `/ui/{context}/setup`, copy the prompt into any AI chat, and paste the response back. This imports your goal, focus areas, and seed questions.
2. **Practice** — pick a context from the home page, choose a focus area, and work through questions. Each answer is evaluated and scored automatically.
3. **Review** — after a session, view results at `/ui/{context}/sessions/{session_id}`. Past attempts at the same question are shown alongside, so you can see whether you're improving.
4. **History** — `/ui/{context}/history` lists all your sessions with attempt counts and average scores.

### Claude Desktop (MCP)

Practice directly inside a Claude Desktop conversation. The MCP server connects
to the running FastAPI app and exposes three tools:

| Tool | What it does |
|---|---|
| `get_question` | Fetches a question from the bank for a context and optional focus area |
| `record_attempt` | Records your answer with a score |
| `end_session` | Returns a URL to the session results page |

**One-time setup:**

Add the following to Claude Desktop's `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "learning-tool": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/learning-tool",
        "python",
        "adapters/mcp/server.py"
      ]
    }
  }
}
```

Replace `/absolute/path/to/learning-tool` with the absolute path to this repo.
Restart Claude Desktop after saving. The MCP server requires the FastAPI app
to be running (`make serve`).

## `contexts/`

`contexts/` is gitignored — it holds your personal learning data (knowledge
base, session history, question bank). Create a directory per context and add
your learning material as text or markdown files before ingesting.

## Database migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/en/latest/).
Migrations run automatically on startup — no manual step required.

To roll back a migration:

```bash
uv run alembic -x sqlalchemy.url="sqlite:///contexts/store/<context>/sessions.db" downgrade -1
```

To check the current revision:

```bash
sqlite3 contexts/store/<context>/sessions.db "SELECT * FROM alembic_version;"
```

---

## Dev tooling

### Checks

```bash
make checks   # ruff + mypy + pytest
make test     # pytest only
make coverage # pytest with coverage report
```

### CLI commands

These are lower-level tools used for context setup and debugging. The web UI
covers the same ground for day-to-day use.

```bash
make ingest context=<name> files=<path>                                         # ingest files into a context
make load-questions context=<name> file=<path>                                  # load questions from YAML into the bank
make prompt context=<name> query="<topic>"                                      # print the question prompt without calling the API
make question context=<name> query="<topic>"                                    # generate a single question
make evaluate context=<name> query="<topic>" question="<q>" answer="<a>"       # evaluate a single answer
make practice context=<name> query="<topic>"                                    # interactive CLI practice loop
```
