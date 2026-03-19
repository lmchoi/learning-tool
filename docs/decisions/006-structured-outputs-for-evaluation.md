# ADR 006 — Use structured outputs for evaluation responses

## Status
Accepted

## Context
The evaluation call asks Claude to return structured data — score, strengths, gaps,
missing points, suggested addition, and an optional follow-up question. This data
needs to be programmatically accessible (e.g. to track weak areas over sessions).

Options considered:
- **JSON in prompt** — ask Claude to return JSON, parse the string response. Unreliable:
  Claude sometimes wraps in markdown code fences, adds commentary, or slightly malforms it.
- **XML tags in response** — ask Claude to wrap each field in tags, extract with string
  parsing. More robust than JSON but still manual and fragile.
- **Structured outputs** — pass a Pydantic model to `client.messages.parse()`. Claude
  uses constrained decoding and cannot return tokens that violate the schema.

## Decision
Use the Anthropic SDK's structured outputs via `client.messages.parse()` with a Pydantic
model for `EvaluationResult`. Also apply to `generate_question` for consistency —
replacing manual whitespace stripping with a typed `Question` model.

```python
class EvaluationResult(BaseModel):
    score: int
    strengths: list[str]
    gaps: list[str]
    missing_points: list[str]
    suggested_addition: str
    follow_up_question: str | None

response = await client.messages.parse(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
    output_format=EvaluationResult,
)

result = response.parsed_output  # typed, no parsing needed
```

## Why not XML tags
XML tags in prompts (ADR 004) are for structuring what is *sent* to Claude.
For what Claude sends *back*, structured outputs are more reliable — the model
is constrained at the token level, not just instructed.

## Trade-offs
- `EvaluationResult` must be a Pydantic model, not a dataclass. `UserProfile` and
  `Question` remain dataclasses — a slight inconsistency, but only response models
  that need schema enforcement require Pydantic.
- Structured outputs are in public beta — API may change.

## Revisit if
The structured outputs API changes significantly, or if a future evaluation model
needs fields that are hard to express in a JSON schema.
