# Debug Annotation Skill

Given a flagged annotation ID, load everything the system knew at the time and analyse why the question may have been unhelpful.

## Usage

`/debug-annotation [annotation_id]`

If no annotation ID is given, defaults to the **latest flagged annotation** (highest `flagged_at` timestamp across all context DBs).

Output is split into two clearly labelled sections: **What the system had** (concrete, from DB and files) and **Analysis** (LLM-generated reasoning).

## Steps

### Step 1: Locate the DB and context

Use the session store SQLite DB. Find it via `STORE_DIR` from `core/settings.py`, or ask the user if unclear. The DB is at `$STORE_DIR/<context>/sessions.db`.

If no annotation ID is given, scan all context DBs to find the annotation with the latest `flagged_at` timestamp.

### Step 2: Load concrete data from the DB

Run the following queries against the SQLite DB using the Bash tool:

```sql
-- If no annotation_id given, find latest flagged first:
SELECT a.id, '<context>' as context
FROM annotations a
WHERE a.flagged_at IS NOT NULL
ORDER BY a.flagged_at DESC
LIMIT 1;

-- Annotation + attempt
SELECT
  a.id as annotation_id,
  a.sentiment,
  a.comment,
  a.flagged_at,
  a.target_type,
  att.question_text,
  att.answer_text,
  att.score,
  att.prompt_text,
  att.timestamp
FROM annotations a
JOIN attempts att ON att.id = a.attempt_id
WHERE a.id = <annotation_id>;

-- RAG chunks for this attempt
SELECT chunk_text, score
FROM chunks
WHERE attempt_id = (
  SELECT attempt_id FROM annotations WHERE id = <annotation_id>
)
ORDER BY score DESC;
```

Also load `context.yaml` from `$STORE_DIR/<context>/context.yaml`.

### Step 3: Output — "What the system had"

Print this section with a clear header. Include all concrete data, formatted for readability:

```
## What the system had

### Context
Goal: ...
Focus areas:
  - ...

### Annotation
ID: ...
Sentiment: up/down
Comment: "..."
Flagged at: ...
Target: question/evaluation

### Attempt
Question: ...
Answer: ...
Score: .../10
Timestamp: ...

### RAG chunks retrieved (ordered by similarity score)
1. [score: 0.87] "chunk text..."
2. [score: 0.74] "chunk text..."
...

### Prompt sent to LLM
<full prompt text>
```

### Step 4: Output — "Analysis"

Print this section with a clear header. Work through each area explicitly, showing reasoning:

```
## Analysis
```

**Retrieval assessment**
- Are the chunks relevant to the question asked?
- Do the similarity scores suggest confident or borderline retrieval?
- Is there a mismatch between the chunks and the stated focus areas?
- Verdict: retrieval looks good / retrieval is suspect / retrieval is the likely problem

**Prompt assessment**
- Are the focus areas from `context.yaml` present in the prompt?
- Is the learner's goal clearly framed?
- Any structural issues with how the prompt is constructed?
- Verdict: prompt looks good / prompt has issues / prompt is the likely problem

**Goal alignment**
- Does the question address a stated focus area?
- Is the question pitched at an appropriate level given the source material?
- Would this question actually help the learner prepare for their goal?
- Verdict: aligned / misaligned / unclear

**Root cause**
Categorise as one of:
- **Retrieval problem** — wrong or irrelevant chunks fetched
- **Prompt problem** — focus areas not used, bad framing
- **Data problem** — source material doesn't cover this topic well enough
- **Goal mismatch** — question is technically valid but not useful for this learner's goal
- **Unknown** — not enough signal to determine

**Proposed fix**
One concrete suggestion. Examples:
- Tweak the question generation prompt to better use focus areas
- Update `GOAL.md` to be more specific and reingest
- Add more source material on this topic
- Adjust RAG retrieval k or similarity threshold
- No fix needed — one-off bad question, not systematic

## Notes

- Keep the two sections strictly separate. Never mix DB facts with LLM reasoning.
- If data is missing (e.g. `prompt_text` is null because #118 isn't landed), note it explicitly rather than skipping the section.
- If RAG chunks are missing (e.g. #116 isn't landed), note it and do best-effort analysis on what is available.
- Flag if the annotation looks like a one-off vs a systemic pattern.
