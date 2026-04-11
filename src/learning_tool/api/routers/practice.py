import asyncio
import json
import logging

from fastapi import APIRouter, Form, HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse

from learning_tool.api.deps import _get_bank_store, _get_session_store, templates
from learning_tool.core.evaluation.evaluate import evaluate_answer
from learning_tool.core.evaluation.prompt import build_evaluation_prompt
from learning_tool.core.models import UserProfile
from learning_tool.core.question.generate_gemini import generate_question_gemini
from learning_tool.core.question.prompt import build_question_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_result_json(result_json: str, context_id: str) -> dict[str, object] | None:
    """Parse a result_json string, normalising any string-typed list fields to lists."""
    try:
        result: dict[str, object] = json.loads(result_json)
        for field in ("strengths", "gaps", "missing_points"):
            if isinstance(result.get(field), str):
                result[field] = [result[field]]
        return result
    except json.JSONDecodeError:
        logger.warning("malformed result_json for attempt in session %s", context_id)
        return None


@router.get("/ui/{context_name}/question", response_class=HTMLResponse, include_in_schema=False)
async def get_question_fragment(
    request: Request, context_name: str, query: str, session_id: str
) -> HTMLResponse:
    try:
        results = await asyncio.to_thread(
            request.app.state.retriever.retrieve, context_name, query, k=5
        )
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        logger.warning("404 context not found: %s", context_name)
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    metadata = request.app.state.context_store.load_context(context_name)
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile, metadata)
    question = await generate_question_gemini(prompt, request.app.state.gemini)
    return templates.TemplateResponse(
        request,
        "question.html",
        {
            "context_name": context_name,
            "question": question.text,
            "question_id": question.question_id,
            "query": query,
            "session_id": session_id,
            "form_action": f"/ui/{context_name}/evaluate",
            "skip_path": f"/ui/{context_name}/question",
            "skip_query_param": "query",
        },
    )


@router.post("/ui/{context_name}/evaluate", response_class=HTMLResponse, include_in_schema=False)
async def post_evaluate_fragment(
    request: Request,
    context_name: str,
    question: str = Form(...),
    answer: str = Form(...),
    query: str = Form(...),
    session_id: str = Form(...),
    question_id: str | None = Form(
        default=None
    ),  # always sent by question.html; None only if called outside the UI
) -> HTMLResponse:
    try:
        results = await asyncio.to_thread(
            request.app.state.retriever.retrieve, context_name, query, k=5
        )
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        logger.warning("404 context not found: %s", context_name)
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    metadata = request.app.state.context_store.load_context(context_name)
    profile = UserProfile(experience_level="beginner")
    prompt = build_evaluation_prompt(
        question=question, answer=answer, chunks=chunks, profile=profile, metadata=metadata
    )
    result = await evaluate_answer(prompt, request.app.state.anthropic)
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    attempt_id = session_store.record(
        session_id,
        question,
        answer,
        result.score,
        question_id=question_id,
        result_json=result.model_dump_json(),
    )
    session_store.record_chunks(attempt_id, results)
    return templates.TemplateResponse(
        request,
        "feedback.html",
        {
            "context_name": context_name,
            "result": result,
            "session_id": session_id,
            "question_id": question_id,
        },
    )


@router.post("/ui/{context_name}/submit", response_class=HTMLResponse, include_in_schema=False)
async def post_submit_fragment(
    request: Request,
    context_name: str,
    question: str = Form(...),
    answer: str = Form(...),
    query: str = Form(...),
    session_id: str = Form(...),
    question_id: str | None = Form(default=None),
) -> HTMLResponse:
    bank_store = _get_bank_store(
        request.app.state.bank_stores, request.app.state.store_dir, context_name
    )
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    next_question, _ = await asyncio.gather(
        asyncio.to_thread(bank_store.get_random, query),
        asyncio.to_thread(
            session_store.record, session_id, question, answer, None, question_id, None
        ),
    )
    if next_question is None:
        return templates.TemplateResponse(
            request,
            "bank_empty.html",
            {"context_name": context_name, "focus_area": query, "session_id": session_id},
        )
    return templates.TemplateResponse(
        request,
        "question.html",
        {
            "context_name": context_name,
            "question": next_question.question,
            "question_id": next_question.id,
            "query": query,
            "session_id": session_id,
            "form_action": f"/ui/{context_name}/submit",
            "skip_path": f"/ui/{context_name}/question/bank",
            "skip_query_param": "focus_area",
        },
    )


@router.get(
    "/ui/{context_name}/sessions/{session_id}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def get_session_results(request: Request, context_name: str, session_id: str) -> HTMLResponse:
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    session = session_store.load_session(session_id)
    if session is None:
        return templates.TemplateResponse(
            request,
            "session.html",
            {"context_name": context_name, "session": None, "attempts": []},
            status_code=404,
        )
    attempts = [
        {
            "attempt": a,
            "result": _parse_result_json(a.result_json, session_id) if a.result_json else None,
        }
        for a in session.attempts
    ]
    return templates.TemplateResponse(
        request,
        "session.html",
        {"context_name": context_name, "session": session, "attempts": attempts},
    )


@router.get("/ui/{context_name}/history", response_class=HTMLResponse, include_in_schema=False)
async def get_history(
    request: Request,
    context_name: str,
    matched: int | None = None,
    unmatched: str | None = None,
) -> HTMLResponse:
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    raw_sessions = session_store.load_sessions()
    sessions = []
    for s in reversed(raw_sessions):
        if not s.attempts:
            continue
        attempts = [
            {
                "attempt": a,
                "result": _parse_result_json(a.result_json, s.session_id)
                if a.result_json
                else None,
            }
            for a in s.attempts
        ]
        sessions.append({"session": s, "attempts": attempts})
    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "context_name": context_name,
            "sessions": sessions,
            "matched": matched,
            "unmatched": unmatched,
        },
    )


@router.get(
    "/ui/{context_name}/question/bank", response_class=HTMLResponse, include_in_schema=False
)
async def get_bank_question_fragment(
    request: Request,
    context_name: str,
    focus_area: str,
    session_id: str,
) -> HTMLResponse:
    bank_store = _get_bank_store(
        request.app.state.bank_stores, request.app.state.store_dir, context_name
    )
    question = await asyncio.to_thread(bank_store.get_random, focus_area)
    if question is None:
        return templates.TemplateResponse(
            request,
            "bank_empty.html",
            {"context_name": context_name, "focus_area": focus_area, "session_id": session_id},
        )
    return templates.TemplateResponse(
        request,
        "question.html",
        {
            "context_name": context_name,
            "question": question.question,
            "question_id": question.id,
            "query": focus_area,
            "session_id": session_id,
            "form_action": f"/ui/{context_name}/submit",
            "skip_path": f"/ui/{context_name}/question/bank",
            "skip_query_param": "focus_area",
        },
    )
