#!/usr/bin/env bash
# PreToolUse: block git commit if ruff or mypy fail.
# Exit code 2 = blocking error shown to Claude.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

[[ "$COMMAND" == *"git commit"* ]] || exit 0

PROJECT_ROOT=$(git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse --show-toplevel 2>/dev/null) || exit 0
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
    echo -e "Pre-commit checks failed:\n$OUTPUT" >&2
    exit 2
fi

exit 0
