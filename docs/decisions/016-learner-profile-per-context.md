# ADR 016 — Learner profile is per-context

## Status
Accepted

## Context
Issue #106. Before building session history or adaptive question generation, we
need to decide where learner proficiency lives — scoped to a context or global
across all contexts.

## Decision
Per-context. The learner profile lives alongside the context it belongs to, stored
under `{store_dir}/{context}/`.

## Rationale
- A user's proficiency in a job-interview context differs in angle from a study
  context, even when the underlying skill overlaps. Keeping them separate is
  accurate, not a limitation.
- Simpler data model: no join across contexts, no global store to bootstrap.
- Migration to per-user is low-cost at this scale (one user, 2–3 contexts): a
  script that reads all context profiles and merges them is straightforward if
  the need ever arises.

## --force reingest
The profile must not be wiped by `--force` reingest. Keep the profile file
separate from the vector store data so reingest only touches chunks and embeddings.

## Revisit if
The tool becomes multi-user, or a user wants a single proficiency view spanning
all their contexts (e.g. a dashboard). At that point a per-user aggregate layer
on top of per-context profiles would be the natural addition.
