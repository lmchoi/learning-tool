import asyncio
import logging

from fastapi import APIRouter, Form, HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from learning_tool.api.deps import _get_bank_store, _get_session_store, templates
from learning_tool.core.context_name import validate_context_name
from learning_tool.core.evaluation.export_prompt import build_export_prompt
from learning_tool.core.evaluation.paste_back import parse_paste_back
from learning_tool.core.models import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/ui/{context_name}/capture", response_class=HTMLResponse, include_in_schema=False)
async def get_capture(request: Request, context_name: str) -> HTMLResponse:
    try:
        validate_context_name(context_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    bank_store = _get_bank_store(
        request.app.state.bank_stores, request.app.state.store_dir, context_name
    )
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    question, session_id = await asyncio.gather(
        asyncio.to_thread(bank_store.get_random),
        asyncio.to_thread(session_store.start_session),
    )
    if question is None:
        raise HTTPException(status_code=404, detail=f"No questions in bank for '{context_name}'")
    return templates.TemplateResponse(
        request,
        "capture.html",
        {
            "context_name": context_name,
            "question": question.question,
            "question_id": question.id,
            "session_id": session_id,
        },
    )


@router.post("/ui/{context_name}/capture", response_class=HTMLResponse, include_in_schema=False)
async def post_capture(
    request: Request,
    context_name: str,
    question: str = Form(...),
    answer: str = Form(...),
    session_id: str = Form(...),
    question_id: str | None = Form(default=None),
) -> HTMLResponse:
    try:
        validate_context_name(context_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    bank_store = _get_bank_store(
        request.app.state.bank_stores, request.app.state.store_dir, context_name
    )
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    # get_random may repeat questions already seen this session — intentional for now;
    # session-aware deduplication can be added later if needed.
    next_question, _ = await asyncio.gather(
        asyncio.to_thread(bank_store.get_random),
        asyncio.to_thread(session_store.record, session_id, question, answer, 0, question_id, None),
    )
    if next_question is None:
        return templates.TemplateResponse(
            request,
            "capture_done.html",
            {"context_name": context_name, "session_id": session_id},
        )
    return templates.TemplateResponse(
        request,
        "capture.html",
        {
            "context_name": context_name,
            "question": next_question.question,
            "question_id": next_question.id,
            "session_id": session_id,
        },
    )


@router.get(
    "/ui/{context_name}/capture/export", response_class=HTMLResponse, include_in_schema=False
)
async def get_capture_export(request: Request, context_name: str, session_id: str) -> HTMLResponse:
    try:
        validate_context_name(context_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    session, metadata = await asyncio.gather(
        asyncio.to_thread(session_store.load_session, session_id),
        asyncio.to_thread(request.app.state.context_store.load_context, context_name),
    )
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    # TODO(#194): load real learner profile from context store instead of hardcoding beginner
    profile = UserProfile(experience_level="beginner")
    prompt = build_export_prompt(session.attempts, profile, metadata)
    return templates.TemplateResponse(
        request,
        "capture_export.html",
        {"context_name": context_name, "prompt": prompt, "session_id": session_id},
    )


@router.post(
    "/ui/{context_name}/capture/paste-back", response_class=HTMLResponse, include_in_schema=False
)
async def post_capture_paste_back(
    request: Request,
    context_name: str,
    session_id: str = Form(...),
    evaluation_text: str = Form(...),
) -> RedirectResponse:
    try:
        validate_context_name(context_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    results = parse_paste_back(evaluation_text)
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )

    matched_count = 0
    unmatched_ids = []
    for aid, eval_res in results:
        updated = session_store.update_attempt_result(
            aid, eval_res.score, eval_res.model_dump_json()
        )
        if updated:
            matched_count += 1
        else:
            unmatched_ids.append(str(aid))

    logger.info(
        "paste-back complete: context=%s session=%s blocks=%d matched=%d unmatched=%d",
        context_name,
        session_id,
        len(results),
        matched_count,
        len(unmatched_ids),
    )
    # Redirect to history (query params for a simple "flash" message)
    url = f"/ui/{context_name}/history?matched={matched_count}"
    if unmatched_ids:
        url += f"&unmatched={','.join(unmatched_ids)}"
    return RedirectResponse(url=url, status_code=303)
