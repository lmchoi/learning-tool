#!/usr/bin/env bash
# PreToolUse: block git commit if ruff or mypy fail.
# Exit code 2 = blocking error shown to Claude.
# pytest is excluded — it's slow and left to manual runs or CI.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

[[ "$COMMAND" == *"git commit"* ]] || exit 0

# $CLAUDE_PROJECT_DIR is set by Claude Code to the project root.
# Falls back to . if running outside Claude Code.
PROJECT_ROOT=$(git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse --show-toplevel 2>/dev/null) || exit 0

# Check branches across all worktrees. If every checked-out worktree branch is
# "main" (or HEAD is detached) then this commit is targeting main — block it.
# If any worktree is on a feature branch, the commit is likely targeting that
# worktree and should be allowed through.
ANY_FEATURE_BRANCH=$(git -C "$PROJECT_ROOT" worktree list --porcelain 2>/dev/null | awk '/^branch / { b=$2; sub("refs/heads/","",b); if (b != "main") print b }' | head -1)

CURRENT_BRANCH=$(git -C "$PROJECT_ROOT" branch --show-current 2>/dev/null)
if [[ "$CURRENT_BRANCH" == "main" && -z "$ANY_FEATURE_BRANCH" ]]; then
    echo "ERROR: Do not commit directly to main. Create a feature branch first." >&2
    exit 2
fi

cd "$PROJECT_ROOT" || exit 0

ERRORS=""
OUTPUT=""

if ! OUT=$(uv run ruff check . 2>&1); then
    ERRORS+="ruff check failed\n"
    OUTPUT+="$OUT\n"
fi

if ! OUT=$(uv run ruff format --check . 2>&1); then
    ERRORS+="ruff format check failed\n"
    OUTPUT+="$OUT\n"
fi

if ! OUT=$(uv run mypy . 2>&1); then
    ERRORS+="mypy failed\n"
    OUTPUT+="$OUT\n"
fi

if [[ -n "$ERRORS" ]]; then
    printf "Pre-commit checks failed:\n%s\n" "$OUTPUT" >&2
    exit 2
fi

exit 0
