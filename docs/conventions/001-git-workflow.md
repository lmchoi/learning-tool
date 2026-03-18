# Convention — Git workflow

## Branches
- `main` is always deployable — never commit directly to it
- All work happens on a branch: `feature/`, `fix/`, `setup/`, `docs/`
- Branch names are lowercase, hyphenated

## Pull requests
- Every change goes through a PR, including tooling and docs
- PR title is short and imperative ("Add ingestion pipeline", not "Added...")
- PR body leads with what you can do after the change, not what files changed

## Commits
- Commit messages explain why, not what
- One logical change per commit — don't bundle unrelated changes
- This applies to docs too — each ADR, convention, or log entry is its own commit
- No "fix" commits before a PR is raised — use `git commit --fixup` and rebase to squash into the original
- Pre-commit hooks run ruff and mypy on every commit
