import logging

from fastapi import APIRouter, Form, HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse

from learning_tool.api.deps import _get_session_store, templates

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/annotate/form", response_class=HTMLResponse, include_in_schema=False)
async def get_annotate_form(
    request: Request,
    question_id: str,
    context_name: str,
    sentiment: str,
) -> HTMLResponse:
    if sentiment not in ("up", "down"):
        logger.warning("422 invalid sentiment: %r", sentiment)
        raise HTTPException(status_code=422, detail="sentiment must be 'up' or 'down'")
    return templates.TemplateResponse(
        request,
        "annotation_form.html",
        {"question_id": question_id, "context_name": context_name, "sentiment": sentiment},
    )


@router.post("/annotate", response_class=HTMLResponse, include_in_schema=False)
async def post_annotate(
    request: Request,
    question_id: str = Form(...),
    context_name: str = Form(...),
    sentiment: str = Form(...),
    comment: str | None = Form(default=None),
) -> HTMLResponse:
    if sentiment not in ("up", "down"):
        logger.warning("422 invalid sentiment: %r", sentiment)
        raise HTTPException(status_code=422, detail="sentiment must be 'up' or 'down'")
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    session_store.record_annotation(question_id, "question", sentiment, comment or None)
    return templates.TemplateResponse(
        request,
        "annotated.html",
        {"sentiment": sentiment, "question_id": question_id, "context_name": context_name},
    )


@router.get("/report-evaluation/form", response_class=HTMLResponse, include_in_schema=False)
async def get_report_evaluation_form(
    request: Request,
    question_id: str,
    context_name: str,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "evaluation_report_form.html",
        {"question_id": question_id, "context_name": context_name},
    )


@router.post("/report-evaluation", response_class=HTMLResponse, include_in_schema=False)
async def post_report_evaluation(
    request: Request,
    question_id: str = Form(...),
    context_name: str = Form(...),
    comment: str = Form(...),
) -> HTMLResponse:
    if not comment.strip():
        logger.warning("422 empty comment on evaluation report for question_id=%s", question_id)
        raise HTTPException(status_code=422, detail="comment is required")
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    session_store.record_annotation(question_id, "evaluation", "down", comment)
    return templates.TemplateResponse(request, "evaluation_reported.html", {})
