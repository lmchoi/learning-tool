ENV_FILE ?= $(HOME)/.secrets/.env
-include $(ENV_FILE)
export

.PHONY: init ingest prompt question evaluate practice serve checks test help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  %-12s %s\n", $$1, $$2}'

init:  ## Initialise a context from a source folder  — source=<dir> context=<name> [force=1]
	uv run learn init --source $(source) --context $(context) $(if $(force),--force,)

ingest:  ## Ingest files into a context  — context=<name> files=<paths>
	uv run learn ingest-context $(context) $(files)

prompt:  ## Print the question prompt without calling the API  — context=<name> query=<topic>
	uv run learn question-prompt $(context) "$(query)"

question:  ## Generate a single practice question  — context=<name> query=<topic>
	uv run learn question $(context) "$(query)"

evaluate:  ## Evaluate an answer  — context=<name> query=<topic> question=<q> answer=<a>
	uv run learn evaluate $(context) "$(query)" "$(question)" "$(answer)"

practice:  ## Interactive practice loop  — context=<name> query=<topic>
	uv run learn practice $(context) "$(query)"

serve:  ## Start the API server
	uv run uvicorn api.main:app --reload --reload-dir api --reload-dir core

checks:  ## Run ruff, mypy, and pytest
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .
	uv run pytest

test:  ## Run tests only
	uv run pytest
