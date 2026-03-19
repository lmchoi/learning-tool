# Project Brief — Personalised Learning Tool

## What This Is

A domain-agnostic personalised learning tool. The core tool doesn't 
know what you're learning — it just knows:
- Here is a knowledge base
- Here is a learner profile  
- Here is some configuration
- Generate questions, evaluate answers, ask follow-ups

The first context is Anthropic FDE interview prep. But the tool 
itself is reusable for learning anything — clinical governance, 
asyncio, a new codebase, a regulatory framework.

**The separation that makes this work:**
- The tool itself — domain agnostic, reusable
- The context — what is being learned, pluggable
- The candidate — who is learning, completely personal

---

## The Core Problem It Solves

Generic interview prep tools exist. Generic learning tools exist. 
What doesn't exist is a tool that knows:
- Exactly what the target material says
- Exactly who you are and what you already know
- Exactly where your gaps are
- How to connect your specific experience to the specific requirements

That personalisation only works if the tool, the knowledge base, 
and the learner profile are cleanly separated and composable.

---

## Architecture

```
project/
  core/                         ← the tool, domain agnostic
    ingestion/
      ingest.py                 ← chunk, embed, store any documents
      sources.py                ← load sources from context config
    rag/
      retriever.py              ← semantic search over ChromaDB
      embeddings.py             ← embedding model setup
    modes/
      practice.py               ← question generation
      evaluate.py               ← answer evaluation / LLM-as-judge
      socratic.py               ← follow-up question generation
      query.py                  ← knowledge base query mode
    voice/
      transcribe.py             ← Faster-Whisper integration
      record.py                 ← microphone capture
    prompts/
      base/                     ← parameterised base templates
        question_gen.py
        evaluator.py
        socratic.py
    models/
      context.py                ← Context, Candidate, LearningConfig dataclasses
    main.py                     ← FastAPI app, loads context at startup

  contexts/                     ← pluggable learning contexts
    anthropic-fde/              ← first context: Anthropic FDE interview
      jd.md                     ← the job description and requirements
      candidate.md              ← background, gaps, stories (gitignored)
      config.yaml               ← tool configuration for this context
      sources.yaml              ← what to ingest
    
    clinical-governance/        ← future: learn DCB0129 deeply
      topic.md
      sources.yaml
      config.yaml
    
    asyncio-python/             ← future: learn asyncio properly
      topic.md
      sources.yaml
      config.yaml

  data/
    chroma/                     ← local vector store, gitignored
  
  .claude/
    CLAUDE.md                   ← project context for Claude Code
    context/                    ← background documents, symlinked to Obsidian

  .gitignore                    ← candidate.md, chroma/, .env
  requirements.txt
  README.md
```

---

## Context Configuration

### config.yaml
How the tool behaves for a specific context:

```yaml
# contexts/anthropic-fde/config.yaml
context_name: anthropic-fde
context_type: interview_prep    # or: topic_learning, skill_practice
display_name: Anthropic FDE Interview Prep

assessment:
  style: conversational         # not whiteboard
  difficulty: senior
  evaluator_tone: demanding     # not encouraging — honest feedback
  
question_types:
  - customer_scenarios
  - technical_conceptual  
  - system_design
  - behavioural
  - live_coding

focus_areas:
  - agent_architecture
  - prompt_engineering
  - evaluation_frameworks
  - healthcare_domain
  - customer_facing_consulting
```

### sources.yaml
What to ingest for this context:

```yaml
# contexts/anthropic-fde/sources.yaml
urls:
  - https://www.anthropic.com/research/building-effective-agents
  - https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
  - https://gist.github.com/kwindla/f755284ef2b14730e1075c2ac803edcf
  - https://job-boards.greenhouse.io/anthropic/jobs/5012991008

local_files:
  - contexts/anthropic-fde/jd.md
  - contexts/anthropic-fde/candidate.md
  - .claude/context/architecture-decisions.md
  - .claude/context/project-context.md
  - .claude/context/study-plan.md
```

### jd.md
The role requirements — what is being assessed against:

```markdown
# Anthropic Forward Deployed Engineer — Requirements

## Role Summary
Embed with strategic customers, build production applications 
with Claude, deliver technical artifacts, feed field intelligence 
back to product teams.

## Key Requirements
- 4+ years technical customer-facing experience
- Production LLM experience — prompting, agents, evals, deployment
- Strong Python
- Healthcare/enterprise vertical experience a plus
- MCP servers, sub-agents, agent skills

## Interview Dimensions
1. Technical Conceptual
2. System Design
3. Customer Scenarios
4. Live Coding
5. Behavioural

## What They're Actually Assessing
[detailed notes on what each dimension looks for]
```

### candidate.md — gitignored, never committed
The learner profile — completely personal:

```markdown
# Candidate Profile — Mandy

## Background
- Staff Engineer at UK healthcare company
- ThoughtWorks consulting background — pair programming, cross-industry
- Leading clinical voice AI project — ElevenLabs, Claude, state machine
- Previously Engineering Manager at same company

## Strong Areas
- Agent architecture and tool use patterns
- Prompt engineering — lean formats, context injection
- Healthcare domain — NHS, GDPR, DCB0129, clinical governance
- ThoughtWorks consulting — pair programming, architecture reviews
- Communicating AI to non-technical clinical stakeholders

## Gaps to Probe
- Evaluation frameworks — designed, not fully built
- RAG — understand deeply, not built one yet  
- MCP server — not built
- Production deployment at scale
- Python/asyncio — rusty

## Stories to Draw Out
- State machine architecture decision and why
- Pushing for eval frameworks before business knew what they wanted
- Clinical safety docs — deterministic vs probabilistic AI explanation
- ThoughtWorks pair programming example
- Identifying wrong problem — human agents are the moat

## Tone Preference
- Direct feedback, not encouraging fluff
- Flag specific gaps, not general "good job"
- Connect to Anthropic's actual vocabulary and thinking
```

---

## Core Data Models

```python
# core/models/context.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CandidateProfile:
    name: str
    background: str
    strong_areas: List[str]
    gaps: List[str]
    stories: List[str]
    tone_preference: str

@dataclass  
class LearningContext:
    context_name: str
    context_type: str  # interview_prep | topic_learning | skill_practice
    jd_or_topic: str
    candidate: CandidateProfile
    config: dict
    sources: List[str]

@dataclass
class Question:
    text: str
    question_type: str
    target_gap: Optional[str]
    relevant_experience: Optional[str]
    difficulty: str

@dataclass
class EvaluationResult:
    score: int  # 1-10
    strengths: List[str]
    gaps: List[str]
    missing_points: List[str]
    suggested_addition: str
    follow_up_question: Optional[str]
```

---

## Parameterised Prompts

The interesting work. Prompts take the context as input:

```python
# core/prompts/base/question_gen.py

QUESTION_GEN_PROMPT = """
You are helping {candidate.name} prepare for {context.display_name}.

About the candidate:
{candidate.background}

Their strong areas: {candidate.strong_areas}
Their gaps to probe: {candidate.gaps}

What is being assessed:
{context.jd_or_topic}

Relevant context from knowledge base:
{retrieved_context}

Generate a {config.assessment.style} question that:
- Is realistic for this specific role/topic
- Targets one of their gaps OR draws on their specific experience
- Would be asked by someone senior at this organisation
- Is NOT generic — it should only make sense for this specific 
  candidate and context

Question type: {question_type}

Return only the question. No preamble.
"""

EVALUATOR_PROMPT = """
You are evaluating an answer for {context.display_name}.

The question was: {question}

The candidate's answer: {answer}

What the target material actually says:
{retrieved_context}

Evaluate with tone: {config.assessment.evaluator_tone}

Return a JSON object:
{{
  "score": <1-10>,
  "strengths": ["..."],
  "gaps": ["..."],
  "missing_points": ["specific things not covered"],
  "suggested_addition": "one concrete improvement",
  "follow_up_question": "what a real interviewer would ask next"
}}

Be honest. If the answer is weak, say so specifically.
Do not be encouraging for its own sake.
"""
```

---

## Tech Stack

- **Python 3.11+** — async throughout
- **FastAPI** — async API layer, simple to deploy
- **Faster-Whisper** — local STT, free, runs on CPU
- **ChromaDB** — local vector store, no infrastructure
- **sentence-transformers** — embeddings, runs locally
- **Claude API** — question generation, evaluation, Socratic mode
- **httpx** — async HTTP for document fetching
- **pyyaml** — config loading
- **Railway** — deployment

---

## Asyncio Throughout

This is also asyncio practice. Use async patterns deliberately:

```python
async def process_answer(
    audio_file: str, 
    question: Question,
    context: LearningContext
) -> EvaluationResult:
    
    # Transcription and context retrieval are independent — run together
    transcript, relevant_context = await asyncio.gather(
        transcribe(audio_file),
        retrieve_context(question.text, context)
    )
    
    evaluation = await evaluate_answer(
        transcript, 
        question,
        relevant_context,
        context
    )
    
    return evaluation

async def ingest_sources(sources: List[str]) -> None:
    tasks = [ingest_source(s) for s in sources]
    await asyncio.gather(*tasks)
```

---

## API Routes

```
POST /contexts/{context_name}/ingest          ← ingest knowledge base
GET  /contexts/{context_name}/question        ← generate practice question
POST /contexts/{context_name}/evaluate        ← evaluate typed answer
POST /contexts/{context_name}/evaluate/voice  ← evaluate voice answer
POST /contexts/{context_name}/followup        ← Socratic follow-up
GET  /contexts/{context_name}/query           ← query knowledge base
GET  /contexts/                               ← list available contexts
```

Context is always a route parameter — same endpoints work for 
any learning context.

---

## What Done Looks Like

### MVP — minimum viable, deployable
- Load a context from config
- Ingest sources from sources.yaml
- Generate a practice question
- Evaluate a typed answer with score and specific feedback
- Deploy to Railway, real URL, works end to end

### Full version
- Voice input via Faster-Whisper
- Socratic follow-up mode
- Knowledge base query mode
- Session history — track practiced questions
- Weak area tracking — surfaces recurring gaps
- Multiple contexts working simultaneously

---

## What I Want to Learn

In priority order:
1. Asyncio patterns — real pipeline, not toy examples
2. RAG implementation — chunking, embedding, retrieval, injection
3. LLM-as-judge eval pattern
4. Parameterised prompt engineering
5. Clean software architecture — separation of concerns
6. Production deployment workflow

---

## Build Order

1. **Data models** — get the shapes right first
2. **Ingestion pipeline** — fetch, chunk, embed, store
3. **RAG retriever** — semantic search, test with real query
4. **Question generation** — load context, retrieve, generate
5. **Answer evaluation** — return EvaluationResult JSON
6. **FastAPI routes** — wire together, test end to end
7. **Deploy to Railway** — real URL
8. **Voice input** — Faster-Whisper
9. **Socratic mode** — follow-up questions
10. **Second context** — prove abstraction works

---

## Notes for Claude Code

- Read .claude/context/ before starting
- candidate.md is gitignored — create locally, never commit
- Start with data models and ingestion
- The interesting work is in the prompts — spend time there
- Use async throughout deliberately — learning objective
- ChromaDB persists to data/chroma/ — gitignore it
- The abstraction is the point — if hardcoded to anthropic-fde it's wrong
- Ask clarifying questions about prompt intent before implementing