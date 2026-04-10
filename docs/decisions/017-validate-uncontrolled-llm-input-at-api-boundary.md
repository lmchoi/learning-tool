# ADR 017 — Validate uncontrolled LLM input at the API boundary using the domain model

## Status
Accepted

## Context
Issue #242. The MCP `record_attempt` tool accepts `evaluation: dict[str, object]` from
the caller's LLM. Tool definitions are soft guidance — unlike structured outputs (ADR-006),
there is no enforcement when an external LLM calls our tool. An LLM can pass
`"strengths": "Good structure."` (a string) instead of `["Good structure."]` (a list).

`POST /api/attempts` was storing it verbatim via `json.dumps(body.evaluation)`. When the
history template iterated `{% for s in item.result.strengths %}`, Jinja2 iterated the string
character-by-character — one `<li>` per character.

## Decision
- Add a `field_validator` to `EvaluationResult` (`core/models.py`) for `strengths`, `gaps`,
  and `missing_points` that coerces `str → [str]`. Be lenient at the model boundary for
  uncontrolled input.
- Change `AttemptRequest.evaluation` from `dict[str, object]` to `EvaluationResult`
  (`api/models.py`). This runs validation at the API boundary using the domain model.
- Store via `body.evaluation.model_dump_json()` instead of `json.dumps(body.evaluation)`.

## Rationale
Structured outputs (ADR-006) apply only when *we* call the LLM. When an LLM calls *our*
tool, the API boundary is the only control point. Coercing at the model layer means all
callers — MCP, direct API, future integrations — get consistent behaviour without
duplicating the fix.

Using `EvaluationResult` as the request type instead of a loose dict also gives us type
safety throughout the request handler and makes the expected shape explicit in the API.

## Revisit if
The evaluation schema evolves in ways that make strict typing at the boundary impractical
(e.g. provider-specific fields). At that point a dedicated inbound DTO with coercion
validators separate from the domain model would be the natural split.
