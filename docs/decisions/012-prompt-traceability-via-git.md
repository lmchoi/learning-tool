# 012 — Prompt traceability via git history, not stored text

## Decision

Do not store the question generation prompt text alongside each attempt. Use the attempt's `timestamp` and git history to reconstruct which prompt template was active at generation time.

## How to trace

Given an attempt with a known timestamp:

```bash
git log --before="<attempt.timestamp>" --oneline core/question/prompt.py | head -1
```

The top commit is the version of `build_question_prompt` that was live when the question was generated.

## Rationale

- The prompt is largely the RAG chunks (already stored per-attempt via #116) plus a static template. Storing the full text duplicates data already in the DB.
- The template changes infrequently. Git history is an authoritative, zero-cost trace.
- If the template begins changing frequently, a short version string (e.g. `"question_v2"`) stored on the attempt row would be the right next step — cheap in the DB and still human-readable.

## Rejected alternative

Store `prompt_text TEXT` on the attempts table (PR #123). Closed because the size cost is real on every attempt and the debugging value is already covered by stored chunks + git history.
