# ADR 002 — RAG with numpy before ChromaDB

## Status
Accepted

## Context
The tool needs to ground questions and evaluations in the actual learning material.
The two obvious approaches are:

1. **Context stuffing** — load all documents directly into the prompt
2. **RAG** — chunk documents, embed them, retrieve relevant chunks at query time

Context stuffing is simpler but skips chunking and retrieval — concepts worth
understanding properly since they directly affect response quality.

## Decision
Implement RAG from first principles:
- Chunk documents (semantic chunking at paragraph/section boundaries)
- Embed chunks using sentence-transformers
- Store embeddings as numpy arrays
- Retrieve via cosine similarity search

Graduate to ChromaDB when numpy becomes unwieldy.

## Why numpy first
- Forces understanding of what a vector database is actually doing
- Chunking logic doesn't change when swapping storage — the switch to ChromaDB
  is a small, isolated refactor
- For a small knowledge base (tens of documents) numpy is sufficient
- The interesting decisions are in chunking strategy, not storage

## Chunking strategy
Semantic chunking at paragraph/section boundaries rather than fixed token windows.
Documents like markdown articles have natural section breaks — these are better
chunk boundaries than arbitrary token counts.

Key decisions:
- Split at `\n\n` paragraph boundaries
- Overlap between chunks to avoid losing concepts at boundaries
- Attach metadata (source file, section header) to each chunk

## Trade-offs
- More complexity upfront than context stuffing
- numpy falls apart at scale — hundreds of thousands of documents
- sentence-transformers adds a dependency and local compute requirement

## Revisit if
The knowledge base grows large enough that numpy similarity search becomes slow,
or managing the array store becomes unwieldy. At that point swap the storage layer
to ChromaDB — chunking and retrieval logic stays the same.
