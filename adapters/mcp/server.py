"""MCP server entry point.

Runs as a stdio server configured in Claude Desktop's claude_desktop_config.json.
Tools are added in subsequent issues — this is the skeleton only.

Usage:
    uv run python adapters/mcp/server.py
"""

import os
import uuid

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("learning-tool")

# Default to localhost if not specified
API_URL = os.environ.get("LEARN_API_URL", "http://localhost:8000")

# One session per MCP server process lifetime.
# If the server restarts mid-conversation a new session will be created;
# proper session management is deferred to the Learner Progress milestone.
session_id = str(uuid.uuid4())


@mcp.tool()
async def get_question(context: str, focus_area: str | None = None) -> dict[str, str] | str:
    """Fetch a question from the bank for a specific context and optional focus area.

    Args:
        context: The name of the learning context (e.g., 'biology', 'git').
        focus_area: Optional focus area to filter questions (e.g., 'mitochondria').
    """
    url = f"{API_URL}/api/questions/{context}"
    params = {"focus_area": focus_area} if focus_area else {}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            q = resp.json()

            try:
                return {
                    "question_id": q["question_id"],
                    "question": q["question"],
                    "focus_area": q["focus_area"],
                }
            except KeyError as e:
                return f"Unexpected API response shape: missing key {e}"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Context '{context}' not found."
            return f"Error fetching question: {e}"
        except Exception as e:
            return (
                f"Error connecting to API at {API_URL}: {e}. "
                "Make sure the FastAPI server is running."
            )


@mcp.tool()
async def record_attempt(
    context: str,
    question_id: str,
    question: str,
    answer: str,
    evaluation: dict[str, object],
    score: int,
) -> dict[str, object] | str:
    """Record an evaluated attempt for a practice question.

    Call this after evaluating the learner's answer to persist the attempt
    and enable progress tracking.

    Args:
        context: The name of the learning context (e.g., 'biology', 'git').
        question_id: Stable identifier for the question from get_question.
        question: The question text as presented to the learner (may differ from bank).
        answer: The learner's answer.
        evaluation: Structured evaluation dict (score, strengths, gaps, etc.).
        score: Integer score (e.g. 1–10).
    """
    url = f"{API_URL}/api/attempts"
    payload = {
        "context": context,
        "session_id": session_id,
        "question_id": question_id,
        "question": question,
        "answer": answer,
        "evaluation": evaluation,
        "score": score,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data: dict[str, object] = resp.json()
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Context '{context}' not found."
            return f"Error recording attempt: {e}"
        except Exception as e:
            return (
                f"Error connecting to API at {API_URL}: {e}. "
                "Make sure the FastAPI server is running."
            )


if __name__ == "__main__":
    mcp.run(transport="stdio")
