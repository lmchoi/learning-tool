# learning-tool

A domain-agnostic personalised learning tool. The tool doesn't know what you're
learning — you plug in a context (knowledge base + learner profile + config) and
it generates questions, evaluates answers, and asks follow-ups.

## Architecture

```mermaid
C4Component
    title Ingestion pipeline

    Container_Boundary(core, "core") {
        Component(ingest, "ingest", "ingestion/ingest.py", "Orchestrates the pipeline")
        Component(sources, "sources", "ingestion/sources.py", "Loads local file paths from sources.yaml")
        Component(chunker, "chunker", "ingestion/chunker.py", "Splits text into paragraph chunks")
        Component(embedder, "embedder", "ingestion/embedder.py", "Embeds chunks into float32 vectors")
        Component(store, "store", "ingestion/store.py", "Persists chunks and embeddings keyed by context")
    }

    SystemDb(config, "sources.yaml", "Local file paths to ingest")
    System(st, "sentence-transformers", "all-MiniLM-L6-v2")
    SystemDb(disk, "Disk", "chunks.json + embeddings.npy")

    Rel(ingest, sources, "load paths")
    Rel(sources, config, "read paths")
    Rel(sources, chunker, "passes text")
    Rel(chunker, embedder, "passes chunks")
    Rel(embedder, store, "passes embeddings")
    Rel(store, disk, "persist")
    Rel(embedder, st, "encode")
    UpdateLayoutConfig($c4ShapeInRow="5", $c4BoundaryInRow="1")

```

```mermaid
C4Component
    title Retrieval pipeline

    SystemDb(disk, "Disk", "chunks.json + embeddings.npy")
    System(st, "sentence-transformers", "all-MiniLM-L6-v2")

    Container_Boundary(core, "core") {
        Component(store, "store", "ingestion/store.py", "Persists chunks and embeddings keyed by context")
        Component(embedder, "embedder", "ingestion/embedder.py", "Embeds chunks into float32 vectors")
        Component(retriever, "retriever", "rag/retriever.py", "Returns top-k chunks for a query")
        Component(similarity, "similarity", "rag/similarity.py", "Ranks chunks by cosine similarity")
    }

    Rel(store, disk, "read")
    Rel(retriever, store, "loads chunks + embeddings")
    Rel(retriever, embedder, "embeds query")
    Rel(retriever, similarity, "ranks chunks")
    Rel(embedder, st, "encode")
    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

## How it's built

This is a learning-by-building project. Sometimes the more complex approach is
taken — not because it's needed, but because understanding it is the point.
The `docs/` directory captures architectural decisions, engineering conventions,
and concepts encountered along the way.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## Usage

Plug in a context — a folder of documents about whatever you're learning — and the
tool generates practice questions grounded in that material.

### 1. Prepare your context

Create a directory under `contexts/` and add your learning material as text or
markdown files. `contexts/` is gitignored so your personal data stays local.

### 2. Ingest

```bash
make ingest context=<name> files=<path>
# e.g.
make ingest context=biology files=contexts/biology/notes.md
```

### 3. Preview a question prompt

Retrieves relevant chunks and prints the prompt that will be sent to Claude.
Useful for verifying the retrieval is working before wiring up the API.

```bash
make prompt context=<name> query="<your question>"
# e.g.
make prompt context=biology query="what is the role of mitochondria"
```

Use `--experience-level` to tailor the question to the learner:

```bash
uv run learn question-prompt biology "what is the role of mitochondria" --experience-level beginner
```

## Running checks

```bash
make checks
```
