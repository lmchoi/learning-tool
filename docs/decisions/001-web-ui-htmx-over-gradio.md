# ADR 001 — HTMX + FastAPI over Gradio

## Status
Accepted

## Context
The tool needs a web UI. Gradio is the common choice for Python ML/AI projects —
it's fast to get something on screen and requires almost no frontend knowledge.

## Decision
Use HTMX + FastAPI instead of Gradio.

## Reasons
- Gradio couples UI and backend tightly — hard to extend, hard to deploy cleanly
- Gradio's output is recognisably "a Gradio app", which doesn't demonstrate
  frontend or API design ability in a portfolio context
- HTMX + FastAPI keeps the API clean and separable — the same backend could
  serve a different frontend later
- FastAPI is what real production Python services use; Gradio is a prototyping tool
- This is also a learning project — building with HTMX teaches more than
  dropping in a Gradio component

## Trade-offs
- More work upfront — Gradio would have a UI in minutes
- Requires learning HTMX alongside everything else
