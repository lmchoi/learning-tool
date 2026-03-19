# ADR 007 — Model Selection Per Task

## Status
Accepted

## Decision

Use different models for different tasks based on the complexity and consequence of each task.

## Model assignments

| Task | Model | Rationale |
|---|---|---|
| Embeddings (RAG retrieval) | `all-MiniLM-L6-v2` (local) | Tiny, fast, free, runs on CPU. Retrieval quality depends on chunking strategy, not model size. |
| Question generation | Claude Haiku | Needs reasoning and context awareness, but not the hardest task. Haiku is cheap and good enough. |
| Answer evaluation | Claude Sonnet | The most important task. Small/cheap models are sycophantic — they'll say "great answer!" when it isn't. This defeats the entire purpose of the tool. Don't compromise here. |
| Socratic follow-up | Claude Haiku | Generating a probing follow-up is doable with a smaller model if the prompt is tight. |
| STT | Faster-Whisper (local) | Local, free, no round-trip. |

## Rationale

**Answer evaluation is the hardest task.** It must assess the answer against source material, identify specific gaps, reference what the docs actually say, and give honest feedback. Small models (7B) are sycophantic and will flatter weak answers. A model that tells you your weak answers are good defeats the entire purpose of the tool.

**Question generation needs reasoning but is medium complexity.** Needs to understand learner background, retrieved context, and generate a specific non-generic question. 7-8B models would produce generic questions. Haiku is the right trade-off.

**RAG retrieval is not the generative model's job.** The embedding model handles retrieval. Retrieval quality depends on chunking strategy.

## Cost

Claude Haiku: ~$1/million input tokens. A typical session (10 questions, evaluations) is ~50–100K tokens — a few cents per session. Not worth compromising on evaluation quality to save pennies.

## Rejected alternative: fully local

Llama 3.1 70B via Ollama is the smallest model trustworthy for honest evaluation. Requires a decent GPU; slow on CPU. Not worth the setup pain for a personal tool.

## The split: cloud for hard thinking, local for mechanical tasks

```
Embeddings     → all-MiniLM-L6-v2  (local, free)
STT            → Faster-Whisper     (local, free)
Question gen   → Claude Haiku       (cloud, cheap)
Evaluation     → Claude Sonnet      (cloud, quality matters)
Socratic       → Claude Haiku       (cloud, cheap)
```
