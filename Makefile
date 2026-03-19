.PHONY: ingest prompt checks test

ingest:
	uv run learn ingest-context $(context) $(files)

prompt:
	uv run learn question-prompt $(context) "$(query)"

checks:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .
	uv run pytest

test:
	uv run pytest
