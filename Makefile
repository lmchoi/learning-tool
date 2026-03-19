.PHONY: ingest prompt question evaluate checks test

ingest:
	uv run learn ingest-context $(context) $(files)

prompt:
	uv run learn question-prompt $(context) "$(query)"

question:
	uv run learn question $(context) "$(query)"

evaluate:
	uv run learn evaluate $(context) "$(query)" "$(question)" "$(answer)"

checks:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .
	uv run pytest

test:
	uv run pytest
