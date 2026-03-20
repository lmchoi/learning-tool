# ADR 009 — Separate API Schemas from Domain Models

## Status
Accepted

## Decision

API request/response schemas live in `api/models.py`. Domain models live in `core/models.py`. Endpoints map between the two explicitly.

## Rationale

`core/models.py` holds types that the domain logic produces and consumes — `EvaluationResult`, `Question`, `UserProfile`. These are owned by core and must stay domain-agnostic.

API schemas like `EvaluateRequest` and `EvaluationResponse` are owned by the API layer. They exist to deserialise HTTP request bodies and serialise HTTP responses. They have no business in core.

Using the same model for both creates coupling: a change to the API response shape (renaming a field, adding pagination metadata, versioning) would require changing a core domain type. The separation means they can evolve independently.

## Structure

```
core/models.py   — EvaluationResult, Question, UserProfile (domain types)
api/models.py    — EvaluateRequest, EvaluationResponse (API schemas)
```

Endpoints in `api/main.py` call core logic, receive domain types, and map them to API response schemas:

```python
result = await evaluate_answer(prompt, client)       # returns EvaluationResult
return EvaluationResponse(**result.model_dump())     # maps to API schema
```

## Consequence

A small amount of mapping code in each endpoint. For now the schemas are structurally identical to the domain types — the mapping is trivial. The value is that they're free to diverge when needed.

## Rejected alternative: reuse domain models directly as API responses

Simple and works fine when the project is small. Breaks down when the API needs to evolve independently — renaming a JSON field for a frontend, adding API-level metadata, or versioning. Hard to reverse once a frontend depends on the response shape.
