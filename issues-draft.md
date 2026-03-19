# GitHub Issues Draft

---

## Issue 1 — Ingest a knowledge base

**Title:** Ingest a knowledge base from config

**Body:**
Right now there's nowhere to load learning material from. After this, you can
point the tool at a set of documents (local files) via `sources.yaml`, have them
chunked at semantic boundaries, embedded, and stored — ready to be searched.

This is the foundation everything else builds on.

Includes the data models for `LearningContext` and `LearningConfig`.

Acceptance criteria:
- [ ] Running ingest against a `sources.yaml` chunks, embeds, and stores all documents
- [ ] Chunks split at paragraph/section boundaries, not fixed token windows
- [ ] Embeddings stored as numpy arrays alongside metadata (source, chunk index)
- [ ] Multiple sources ingested concurrently
- [ ] Re-running ingest updates cleanly

---

## Issue 2 — Search the knowledge base

**Title:** Search the knowledge base with a natural language query

**Body:**
After ingestion we have chunks and embeddings but no way to query them. After this,
you can ask a question in plain English and get back the most relevant chunks —
retrieved via cosine similarity over numpy arrays.

This is RAG from first principles: no vector database, just embeddings and maths.
The retrieval logic stays the same when we graduate to ChromaDB later.

Acceptance criteria:
- [ ] Given a query, embeds it and returns top-k most relevant chunks via cosine similarity
- [ ] Manually verified: a real query returns meaningfully relevant results
- [ ] Async

---

## Issue 3 — Build the question prompt

**Title:** Build a grounded question prompt from retrieved chunks

**Body:**
After this, the tool can retrieve relevant chunks for a learner's context and
assemble a fully parameterised prompt — ready to send to Claude. No API call yet.

Includes `UserProfile` (`experience_level: str`) and `Question` (`text: str`) data models.

Acceptance criteria:
- [ ] Given a context and learner profile, retrieves relevant chunks and builds a prompt grounded in them
- [ ] CLI command prints the prompt — manually verify it contains relevant retrieved chunks
- [ ] Prompt is fully parameterised — no hardcoded context details
- [ ] Async

---

## Issue 4 — Generate a practice question

**Title:** Generate a context-aware practice question

**Body:**
After this, the tool calls Claude with the prompt built in Issue 3 and returns a
`Question`. The question should only make sense for this specific context and learner —
not answerable from general knowledge.

First real use of the Claude API.

Acceptance criteria:
- [ ] Given a context and learner profile, returns a `Question`
- [ ] Manually verified: question is specific to the knowledge base, not answerable from general knowledge

---

## Issue 5 — Evaluate an answer

**Title:** Evaluate a typed answer and return structured feedback

**Body:**
After this, you can type an answer and get honest, specific feedback: a score,
what you covered well, what you missed, and one concrete thing to add. This is
the core learning loop — question → answer → feedback.

Implements the LLM-as-judge pattern.

Includes the `EvaluationResult` data model.

Acceptance criteria:
- [ ] Returns score 1–10, strengths, gaps, missing points, suggested addition
- [ ] Feedback references the actual knowledge base material, not just general knowledge
- [ ] Prompt is parameterised — tone and style driven by context config
- [ ] Manually verified: weak answer gets honest critical feedback, not encouragement

---

## Issue 6 — Use it via HTTP

**Title:** Expose the learning loop over HTTP (FastAPI)

**Body:**
After this, the tool is usable from anywhere — curl, a browser, a frontend.
Ingest, generate a question, and evaluate an answer all via HTTP. Context is
always a route parameter so the same API works for any learning context.

This is the point where it stops being a script and becomes a deployable service.

Acceptance criteria:
- [ ] `POST /contexts/{context_name}/ingest` — triggers ingestion
- [ ] `GET  /contexts/{context_name}/question` — returns a question
- [ ] `POST /contexts/{context_name}/evaluate` — returns evaluation
- [ ] `GET  /contexts/` — lists available contexts
- [ ] Full round trip works end to end with a real context

---

## Issue 7 — Deploy it

**Title:** Deploy to Railway

**Body:**
After this, the tool has a real URL and works in production. Not just on localhost.

Acceptance criteria:
- [ ] Live URL returns a question for a real context
- [ ] `ANTHROPIC_API_KEY` injected via env var

---

## Issue 8 — Answer by voice

**Title:** Answer practice questions by speaking

**Body:**
After this, you can speak your answer instead of typing it. More natural for
practice — closer to the real thing. Transcription runs concurrently
with retrieval so there's no extra latency cost.

Acceptance criteria:
- [ ] `POST /contexts/{context_name}/evaluate/voice` accepts an audio file
- [ ] Transcribed locally via Faster-Whisper (no external API)
- [ ] Transcription and retrieval run concurrently
- [ ] Evaluation result identical in structure to typed answer route

---

## Issue 9 — Socratic follow-up

**Title:** Get a follow-up question after evaluation

**Body:**
After this, evaluation doesn't just score your answer — it asks what a real
expert would ask next, targeting the specific gap the evaluation surfaced.
Turns a one-shot Q&A into a real back-and-forth.

Acceptance criteria:
- [ ] `POST /contexts/{context_name}/followup` returns a follow-up `Question`
- [ ] Follow-up directly targets a gap from the evaluation result
- [ ] Prompt parameterised — not hardcoded to any context

---

## Issue 10 — Swap numpy for ChromaDB

**Title:** Replace numpy vector store with ChromaDB

**Body:**
After this, the retrieval layer uses ChromaDB instead of numpy arrays. The
chunking and retrieval logic doesn't change — only the storage layer. This is
the point where you understand what a vector database is actually doing for you,
because you've already built the thing it replaces.

Acceptance criteria:
- [ ] ChromaDB replaces numpy arrays as the embedding store
- [ ] Chunking logic unchanged
- [ ] Retrieval interface unchanged — callers see no difference
- [ ] Manually verified: retrieval quality identical to numpy implementation

---

## Issue 11 — Second learning context

**Title:** Plug in a second learning context

**Body:**
After this, we know the abstraction actually works. A completely different topic
— different knowledge base, different config — runs through the same tool with
zero changes to core code. If anything in core needs changing to make it work,
that's a bug.

Acceptance criteria:
- [ ] New context ingested, questions generated, answers evaluated via the same routes
- [ ] Zero changes to `core/`
- [ ] Both contexts work simultaneously
