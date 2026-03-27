# ADR 013 — Scope RAG to large external docs; inject structured context directly

## Status
Proposed — lower urgency given chat integration direction (see note below)

## Context

The current ingestion pipeline chunks and embeds everything — background docs, role description, GOAL.md, and
any other files in the source directory. At question generation time, the top-k chunks
are retrieved and injected into the prompt.

This works for large, unstructured corpora where you don't know which bits are relevant
at query time. But it is the wrong tool for structured, bounded documents like a
background summary or role description, where:

- The full document fits comfortably in a prompt
- Chunking loses structure and introduces retrieval noise
- Retrieval may return irrelevant chunks when a simpler direct injection would be exact

The annotation debug session (#115) surfaced a concrete example: a question about
Python's "We are all responsible users" philosophy was generated because the retriever
pulled chunks from a general Python style guide. The learner's goal (FDE interview
prep) and focus areas were not in the prompt at all — only the retrieved chunks were.
The root cause was that structured context (goal, focus areas, learner background) was not being used
to steer generation.

## Decision

Split the knowledge base into two tiers:

**Tier 1 — Structured context (injected directly into the system prompt)**
- Learner background (e.g. experience summary)
- Target role or goal description
- Goal statement and focus areas (from `context.yaml`)
- Coverage gaps (from `context.yaml`)
- Session history and weak areas

These are small, structured, and always fully relevant. Inject them whole.

**Tier 2 — Reference corpus (chunked, embedded, retrieved via RAG)**
- External docs fetched from URLs (Anthropic docs, Python references, MCP spec, etc.)
- Large supplementary reading material

These are large and unstructured. RAG is the right tool — retrieve top-k chunks
relevant to the current focus area at question generation time.

## What changes

- `init` distinguishes between local structured files and URL-sourced material
- Local structured files (background, role description) are stored as full text, not chunked
- URL-sourced material is chunked and embedded as before
- Question generation prompt includes full structured context in the system prompt,
  plus RAG-retrieved chunks from the reference corpus
- `context.yaml` records which files are structured context vs reference material

## Why this is better

- No retrieval noise from chunking structured docs — the model sees the whole thing
- Focus areas and goal directly steer question generation, not just hint at it
- RAG is used where it adds value (large external docs), not where it doesn't
- Coverage reporting (which focus areas have reference material) becomes meaningful
- Simpler mental model: structured things go in the prompt, large things go in RAG

## Trade-offs

- Local files must be classified as structured context or reference material during
  `init`. The LLM can infer this (short structured docs → direct; long docs → reference), or
  the user can signal it in `GOAL.md` under a `# Sources` section.
- If a structured file is very large (e.g. a 50-page report), direct injection may
  hit context limits. In that case it should be treated as reference material instead.
  The LLM can make this call during init based on token count.
- The vector store becomes reference-corpus-only. Existing contexts with structured docs
  chunked into the store will need to be reinitialised.

## Relationship to other decisions

- Supersedes the implicit assumption in #101–#105 that all local files are chunked
- Complements ADR 012 (prompt traceability) — the system prompt structure is now
  more significant and worth tracking
- Enables the coverage report (focus area → reference chunks) to be meaningful

## Revisit if

The structured context (background docs + session history) grows large enough to approach
context window limits. At that point, selective injection or summarisation of
structured context would be worth considering.

## Note — chat integration design (2026-03-27)

The chat integration direction (see `docs/design/chat-integration-mcp.md`) shifts
question generation and evaluation to the user's LLM chat (Claude Projects). The
user's CV, background docs, and goal are already in Claude's context — the tool
doesn't need to inject Tier 1 structured context for generation if generation happens
in chat.

This ADR remains valid for the **server-side generation fallback** (web practice
loop without MCP), but its urgency is reduced. Tier 2 RAG (external reference docs)
is still relevant for that path. Implement when server-side generation quality becomes
a priority again.
