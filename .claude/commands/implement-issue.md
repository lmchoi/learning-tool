# Implement Issue Skill

Implement a refined GitHub issue inside its worktree. Run this after `/start-issue` has set up the worktree and branch.

## Usage

`/implement-issue`

Run this skill from anywhere. It will automatically cd into the worktree based on the current branch name. No issue number needed — the branch name encodes it.

## Steps

### Step 1: Change into the worktree

Extract the issue number from the current branch name (format: `feat/<number>-<slug>`):
```bash
BRANCH=$(git branch --show-current)
ISSUE_NUM=$(echo $BRANCH | grep -oE '[0-9]+' | head -1)
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT/.claude/worktrees/$ISSUE_NUM-"*
```

### Step 2: Orient yourself

- Run `git branch --show-current` to confirm the branch name and derive the issue number
- Run `gh issue view <number>` to get the full issue spec — problem, solution, acceptance criteria, and the `## Commits` breakdown
- Run `git log main..HEAD --oneline` to see what commits already exist on this branch (if any)

### Step 3: Understand the codebase before writing anything

Read the existing code in the areas you will touch. Follow existing patterns exactly:
- FastAPI routes
- HTMX templates
- Store usage
- Test structure

Do not invent new patterns. If you are unsure where something belongs, read more code first.

### Step 4: Implement commit by commit

Work through the commit breakdown from the issue, one commit at a time.

For each commit:
1. Write the failing test first
2. Implement the code to make it pass
3. Run checks — all must pass before committing:
   ```bash
   make check
   make format-check
   make typecheck
   make test
   ```
4. Commit with a clear message

Never commit a failing test. Never batch multiple logical changes into one commit.

### Step 5: Async discipline

- Use `asyncio.gather` for independent concurrent work
- Use `asyncio.to_thread` for blocking I/O
- Do not use sequential awaits where gather would work

### Step 6: Domain-agnostic discipline

The core is domain-agnostic — it only knows: here is a knowledge base, here is a learner profile, here is config. Do not hardcode domain-specific logic into `core/`.

### Step 7: When done

- Run the full check suite one final time
- Push the branch: `git push`
- Create a PR:
  ```bash
  gh pr create --title "<title>" --body "$(cat <<'EOF'
  <description of changes>
  EOF
  )"
  ```
- Report which commits were made, confirm all checks pass, and provide the PR link
