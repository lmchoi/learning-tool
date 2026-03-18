# GitHub Issues Draft

---

## Issue 1 — Ingest a knowledge base

**Title:** Ingest a knowledge base from config

**Body:**
Right now there's nowhere to load learning material from. After this, you can
point the tool at a set of documents (URLs, local files) via `sources.yaml` and
have them loaded and ready to use.

This is the foundation everything else builds on.

Includes the data models for `LearningContext` and `LearningConfig`.

Acceptance criteria:
- [ ] Running ingest against a `sources.yaml` loads all documents
- [ ] Works with both local files and URLs
- [ ] Multiple sources fetched concurrently
- [ ] Re-running ingest updates cleanly

---

## Issue 2 — Generate a practice question

**Title:** Generate a context-aware practice question

**Body:**
After this, the tool can generate a question that is grounded in the knowledge base
and tailored to the learner — not a generic question a search engine could produce.
The question should only make sense for this specific context and user.

First real use of the Claude API.

Includes `UserProfile` and `Question` data models.

Acceptance criteria:
- [ ] Given a context and question type, returns a `Question`
- [ ] Question is grounded in loaded knowledge base content
- [ ] Prompt is fully parameterised — no hardcoded context details
- [ ] Manually verified: question is specific, not generic

---

## Issue 3 — Evaluate an answer

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

## Issue 4 — Use it via HTTP

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

## Issue 5 — Deploy it

**Title:** Deploy to Railway

**Body:**
After this, the tool has a real URL and works in production. Not just on localhost.

Acceptance criteria:
- [ ] Live URL returns a question for a real context
- [ ] `ANTHROPIC_API_KEY` injected via env var

---

## Issue 6 — Answer by voice

**Title:** Answer practice questions by speaking

**Body:**
After this, you can speak your answer instead of typing it. More natural for
practice — closer to the real thing. Transcription runs concurrently
with context loading so there's no extra latency cost.

Acceptance criteria:
- [ ] `POST /contexts/{context_name}/evaluate/voice` accepts an audio file
- [ ] Transcribed locally via Faster-Whisper (no external API)
- [ ] Transcription and context loading run concurrently
- [ ] Evaluation result identical in structure to typed answer route

---

## Issue 7 — Socratic follow-up

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

## Issue 8 — Second learning context

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

---

## Issue 9 — Warn when context size approaches the limit

**Title:** Add token count warning when context approaches limit

**Body:**
Context stuffing works well for small knowledge bases — but there's no signal
when it starts to degrade. After this, the app logs a warning when context size
approaches Claude's limit, so you know when it's time to consider RAG rather
than discovering it through mysterious response quality issues.

Acceptance criteria:
- [ ] Token count checked before each API call using `client.messages.count_tokens`
- [ ] Warning logged when input tokens exceed a threshold (e.g. 150k)
- [ ] Threshold is configurable, not hardcoded

---

## Issue 9 — Warn when context size approaches the limit

**Title:** Add token count warning when context approaches limit

**Body:**
Context stuffing works well for small knowledge bases — but there's no signal
when it starts to degrade. After this, the app logs a warning when context size
approaches Claude's limit, so you know when it's time to consider RAG rather
than discovering it through mysterious response quality issues.

Acceptance criteria:
- [ ] Token count checked before each API call using `client.messages.count_tokens`
- [ ] Warning logged when input tokens exceed a threshold (e.g. 150k)
- [ ] Threshold is configurable, not hardcoded
