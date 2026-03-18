# ADR 002 — Context stuffing over RAG

## Status
Accepted

## Context
The tool needs to ground questions and evaluations in the actual learning material.
The typical approach for this in AI applications is RAG: chunk documents, embed
them, store in a vector database, retrieve relevant chunks at query time.

## Decision
Load knowledge base documents directly into the prompt (context stuffing) instead
of building a RAG pipeline with a vector store.

## Reasons
- The knowledge base per context is small and focused — a few documents, articles,
  and config files. This fits comfortably in Claude's context window.
- RAG adds significant complexity: chunking strategy, embedding model, vector store
  setup, retrieval tuning. None of that complexity is justified until the data
  outgrows the context window.
- Context stuffing is simpler, faster to build, and easier to reason about.
- The prompt interface stays the same either way — relevant text goes in. Switching
  to RAG later doesn't require restructuring the rest of the system.

## Trade-offs
- Won't scale to very large knowledge bases (a full textbook, a large codebase)
- No semantic search — all loaded material is always in context, not selectively retrieved

## Revisit if
A context's knowledge base grows large enough to hit context window limits, or
if retrieval precision becomes important (i.e. too much irrelevant material is
hurting response quality).

## How to know it's time
- **Hard signal** — API returns a `context_length_exceeded` error
- **Soft signals** — responses feel less grounded or more generic; evaluation
  feedback stops referencing specific material; Claude appears to "miss" things
  that are in the documents. These can look like prompt quality issues — check
  context size first before tuning prompts.

## What changes if we add RAG later
Only the document loading layer. The prompt templates, data models, and API routes
stay the same — RAG would slot in between "load documents" and "build prompt".
