#!/usr/bin/env bash
# PostToolUse: auto-format and lint Python files immediately after Edit/Write.
# Non-blocking — always exits 0.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[[ "$FILE_PATH" == *.py ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

PROJECT_ROOT=$(git -C "$(dirname "$FILE_PATH")" rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$PROJECT_ROOT" || exit 0

uv run ruff format "$FILE_PATH" --quiet
uv run ruff check "$FILE_PATH" --fix --quiet

exit 0
