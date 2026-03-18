# ADR 003 — Domain-agnostic core with pluggable contexts

## Status
Accepted

## Context
The first use case is a specific learning context. The easiest approach
would be to hardcode everything for that use case.

## Decision
Keep `core/` entirely domain-agnostic. All context-specific material (knowledge
base, learner profile, config) lives in `contexts/` and is injected at runtime.
The `contexts/` directory is gitignored entirely.

## Reasons
- A tool hardcoded to one use case is a script; a tool with pluggable contexts
  is a product
- The separation is the interesting engineering challenge — it's what makes this
  worth building
- `contexts/` contains personal data (user profile, study materials) that
  should never be committed
- Proves the abstraction works: adding a second context should require zero
  changes to core

## Trade-offs
- More upfront design work — every data model and prompt must be parameterised
- Easier to accidentally leak context-specific assumptions into core

## Test
If adding a second, completely different learning context requires changes to
`core/`, the abstraction has failed.
