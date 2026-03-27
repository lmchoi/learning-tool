# ADR 014 — Prioritise question bank over on-demand generation

## Status
Accepted — implemented (#132, #50, #131 closed)

## Context

The current practice loop generates a question on demand: RAG retrieves chunks from
the knowledge base, the model produces a question, the learner answers, and the
evaluation runs. This works when the learner has no prior question set and needs the
tool to surface what to practise.

But the primary value of the tool is the practice loop itself — answer, evaluate,
feedback — not question generation. When the learner already has a well-calibrated
set of questions (curated manually, exported from prior sessions, or sourced
externally), on-demand generation adds latency and non-determinism without adding
value. The tool should not force the learner through generation when better material
already exists.

There is also a structural issue: the current page loads directly into question
generation with no way to direct focus. The learner cannot express which topic area
they want to practise before a question appears.

## Decision

The practice page (`/ui/{context}`) is restructured around a question bank as the
primary source:

1. **Page load shows a focus area selector**, drawn from `context.yaml`. The learner
   picks an area (or "any") before a question is shown.

2. **Selecting a focus area serves a question from the bank** for that area. No
   generation, no RAG retrieval — a direct read from the question bank.

3. **A "Generate" button remains available** as an explicit action. It triggers the
   existing generation flow with the selected focus area injected into the prompt.
   The current behaviour is fully preserved; it just becomes opt-in rather than
   the default.

The question bank is populated from a structured file (e.g. `questions.yaml` in the
context directory) via a CLI command. The file is parsed directly into question
records — no chunking, no embedding. This is a distinct path from the RAG ingestion
pipeline and does not interact with the vector store.

## What this deprioritises

- Ingestion pipeline improvements (URL sources, chunking refinements, coverage
  reporting) — still valuable, lower urgency when a bank already exists
- Question generation improvements — still the fallback and explicitly available,
  but no longer the critical path

## Consequences

- The practice loop works end-to-end without any RAG or generation if the bank is
  populated — simpler, faster, more predictable
- Focus area selection becomes the natural entry point for a session, which feeds
  naturally into weak area surfacing and spaced repetition later
- The generate path is preserved and still used when the bank has no question for
  the selected area, or when the learner explicitly wants a generated question

## Implementation order

1. `#132` — Load question bank from file (no chunking) ✓
2. `#50` — Serve questions from bank given a focus area ✓
3. `#131` — Focus area selector on the practice page ✓

## Note — chat integration design (2026-03-27)

The question bank population path has expanded beyond the original CLI command.
Questions can now be imported from an AI chat response via the setup page (#142/#143)
— the user pastes a structured response from Claude and the tool parses it into
`questions.yaml`. This is now the primary population path.

The MCP tool `create_context()` (#169) will further streamline this — Claude calls
the tool directly without a copy-paste step.

The "Generate" button as explicit fallback remains unchanged and aligns with the
chat integration design, where on-demand generation is de-prioritised in favour of
the question bank.

## Revisit if

The question bank proves too rigid — e.g. the learner exhausts the bank and needs
generated questions to fill gaps. At that point, blending bank and generated
questions (weighted by coverage) would be the natural next step.
