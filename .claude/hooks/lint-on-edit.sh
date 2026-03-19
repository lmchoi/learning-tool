#!/usr/bin/env bash
# PostToolUse: auto-format and lint Python files immediately after Edit/Write.
# Runs silently on success; prints errors on failure (non-blocking).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ "$FILE_PATH" == *.py ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

cd "$(dirname "$FILE_PATH")" || exit 0
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$PROJECT_ROOT" || exit 0

uv run ruff format "$FILE_PATH" --quiet 2>&1
uv run ruff check "$FILE_PATH" --fix --quiet 2>&1

exit 0
