# ADR 011 — Session store vs Langfuse: boundary between learner data and observability

## Status
Accepted

## Context
The tool has two places where evaluation data could be stored:

1. **SQLite session store** (introduced in #60) — records what happened in a practice session
2. **Langfuse** (Observability milestone, #19) — LLM observability platform for tracking model calls, scores, and annotations

When designing the session store schema, the question arose: should we store the full `EvaluationResult` (strengths, gaps, missing_points, suggested_addition, follow_up_question, answer text) alongside the score, to support future evaluation quality assessment?

## Decision
No. The session store holds only what is needed for learner-facing features. Evaluation quality and annotations belong to Langfuse.

## Boundary

| Concern | Store |
|---|---|
| What questions were asked this session | SQLite |
| What scores were given | SQLite |
| Session history view (#61) | SQLite |
| Weak area resurfacing (#28) | SQLite |
| Was this score fair? | Langfuse |
| Full evaluation result (strengths, gaps, etc.) | Langfuse |
| Learner annotations on evaluations | Langfuse |
| LLM call traces | Langfuse |

## Why this boundary
- Langfuse captures LLM calls at the point they happen — the full evaluation result is naturally available there without duplicating it in SQLite
- Annotations are a Langfuse first-class feature; re-implementing them in SQLite would be reinventing the wheel
- Keeping SQLite lean avoids schema churn as the evaluation model evolves
- The two stores serve different audiences: SQLite is for the learner, Langfuse is for the developer

## Trade-offs
- If Langfuse is not set up, there is no record of evaluation quality — accepted, since Langfuse integration is a deliberate milestone
- Cannot join learner session data with evaluation quality data in a single query — acceptable for a single-user tool where these concerns are addressed separately
