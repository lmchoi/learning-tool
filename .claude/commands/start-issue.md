# Start Issue Skill

Given a refined GitHub issue number, create a worktree, launch a background subagent to implement it, and move the issue to "In Progress" on the project board.

## Usage

`/start-issue <issue-number>`

The issue must already be refined (design and commit breakdown present in the issue body). If it hasn't been refined yet, run `/refine-issue` first.

## Steps

### Step 1: Fetch the issue

Run `gh issue view <number>` to get the full issue text. Read it carefully — you need the commit breakdown and any design notes.

If the issue body has no `## Commits` section, stop and tell the user to run `/refine-issue <number>` first.

### Step 2: Determine the branch name

Use the format `feat/<number>-<short-slug>` where the slug is a 2-4 word kebab-case summary of the issue title.

Examples:
- #144 "Capture-mode practice page" → `feat/144-capture-mode`
- #187 "Document database schemas" → `feat/187-schema-docs`

### Step 3: Create the worktree

```bash
git worktree add .claude/worktrees/<number>-<slug> -b feat/<number>-<slug>
```

If the branch already exists (worktree was previously created), just confirm it exists and proceed.

### Step 4: Move the issue to In Progress

1. Check if the issue is already in the project:
```bash
gh project item-list 6 --owner lmchoi --format json --limit 100 | python3 -c "
import json,sys
items=json.load(sys.stdin)['items']
item=next((i for i in items if i.get('content',{}).get('number')==<number>),None)
print(item['id'] if item else 'not found')
"
```

2. If not found, add it first:
```bash
gh project item-add 6 --owner lmchoi --url <issue-url>
```
Then re-run the lookup.

3. Set status to In Progress:
```bash
gh project item-edit --project-id PVT_kwHOAHDUcM4BSQiR --id <item-id> --field-id PVTSSF_lAHOAHDUcM4BSQiRzg_2JWs --single-select-option-id 194746c4
```

### Step 5: Launch the background subagent

Launch an Agent with `run_in_background: true`. The agent prompt must include:

- The worktree path: `/Users/mandy/workspace/learning-tool/.claude/worktrees/<number>-<slug>`
- The branch name
- The full issue spec (problem, solution, acceptance criteria, commit breakdown)
- These standing instructions:
  - Work entirely within the worktree — do not touch the main working directory
  - Read existing code before writing anything — follow existing patterns exactly (FastAPI routes, HTMX templates, store usage, etc.)
  - Each commit must be a complete red→green cycle — never commit a failing test
  - Run checks before each commit:
    ```
    cd <worktree-path>
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy .
    uv run pytest
    ```
  - Async throughout — use `asyncio.gather` for independent work, `asyncio.to_thread` for blocking I/O
  - Do not push, do not create a PR
  - The codebase is domain-agnostic — do not hardcode domain-specific logic into core

### Step 6: Confirm to the user

Tell the user:
- The branch name and worktree path
- That the issue has been moved to In Progress
- That the agent is running in the background
