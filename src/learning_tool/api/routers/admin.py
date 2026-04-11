import json
import logging

import httpx
from fastapi import APIRouter, Form, HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from learning_tool.api.deps import _get_session_store, templates
from learning_tool.core.context_name import validate_context_name
from learning_tool.core.settings import GITHUB_REPO, GITHUB_TOKEN

logger = logging.getLogger(__name__)

router = APIRouter()

_GITHUB_CONFIGURED = bool(GITHUB_TOKEN and GITHUB_REPO)
_VALID_TARGET_TYPES = {"question", "evaluation"}
_VALID_SENTIMENTS = {"up", "down"}


async def _create_github_issue(ann: dict[str, object], annotation_id: int) -> str:
    raw_rj = ann.get("result_json")
    result = json.loads(raw_rj) if isinstance(raw_rj, str) else {}
    gaps = "\n".join(f"- {g}" for g in result.get("gaps", [])) or "N/A"
    body = (
        f"**Type:** {ann['target_type']}\n"
        f"**Sentiment:** {ann['sentiment']}\n"
        f"**Question:** {ann['question_text']}\n"
        f"**Answer:** {ann['answer_text']}\n"
        f"**Score:** {ann['score']}/10\n"
        f"**Evaluation gaps:**\n{gaps}\n"
        f'**Learner comment:** "{ann.get("comment") or ""}"\n'
    )
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/issues",
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "title": f"Feedback quality: {ann['target_type']} annotation #{annotation_id}",
                "body": body,
                "labels": ["feedback-quality"],
            },
        )
    if resp.status_code not in (200, 201):
        logger.error(
            "502 GitHub API error: status=%d annotation_id=%d", resp.status_code, annotation_id
        )
        raise HTTPException(status_code=502, detail="GitHub API error")
    return str(resp.json().get("html_url", ""))


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def get_admin_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin_index.html")


@router.get("/admin/contexts", response_class=HTMLResponse, include_in_schema=False)
async def get_admin_contexts(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin_contexts.html", {"error": None})


@router.post(
    "/admin/contexts", response_class=HTMLResponse, response_model=None, include_in_schema=False
)
async def post_admin_contexts(
    request: Request,
    name: str = Form(...),
) -> HTMLResponse | RedirectResponse:
    try:
        validate_context_name(name)
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "admin_contexts.html",
            {"error": str(e)},
            status_code=400,
        )
    return RedirectResponse(url=f"/ui/{name}/setup", status_code=303)


@router.get("/admin/annotations", response_class=HTMLResponse, include_in_schema=False)
async def get_admin_annotations(
    request: Request,
    context_name: str,
    target_type: str | None = None,
    sentiment: str | None = None,
    flagged: bool = False,
) -> HTMLResponse:
    if target_type is not None and target_type not in _VALID_TARGET_TYPES:
        logger.warning("422 invalid target_type: %r", target_type)
        raise HTTPException(
            status_code=422, detail=f"target_type must be one of {_VALID_TARGET_TYPES}"
        )
    if sentiment is not None and sentiment not in _VALID_SENTIMENTS:
        logger.warning("422 invalid sentiment: %r", sentiment)
        raise HTTPException(status_code=422, detail=f"sentiment must be one of {_VALID_SENTIMENTS}")
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    raw = session_store.load_annotations(
        target_type=target_type, sentiment=sentiment, flagged=flagged
    )
    for ann in raw:
        rj = ann.get("result_json")
        ann["result"] = json.loads(rj) if isinstance(rj, str) else None
    return templates.TemplateResponse(
        request,
        "admin_annotations.html",
        {
            "context_name": context_name,
            "annotations": raw,
            "target_type": target_type or "",
            "sentiment": sentiment or "",
            "flagged": flagged,
            "github_configured": _GITHUB_CONFIGURED,
        },
    )


@router.post(
    "/admin/annotations/{annotation_id}/escalate",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def post_escalate_annotation(
    request: Request,
    annotation_id: int,
    context_name: str,
) -> HTMLResponse:
    if not _GITHUB_CONFIGURED:
        logger.error("503 GitHub escalation not configured")
        raise HTTPException(status_code=503, detail="GitHub escalation is not configured")
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    ann = session_store.load_annotation(annotation_id)
    if ann is None:
        logger.warning("404 annotation not found: id=%d", annotation_id)
        raise HTTPException(status_code=404, detail="Annotation not found")
    issue_url = await _create_github_issue(ann, annotation_id)
    return templates.TemplateResponse(
        request,
        "escalated.html",
        {"issue_url": issue_url, "annotation_id": annotation_id},
    )


@router.post(
    "/admin/annotations/{annotation_id}/flag", response_class=HTMLResponse, include_in_schema=False
)
async def post_flag_annotation(
    request: Request,
    annotation_id: int,
    context_name: str,
) -> HTMLResponse:
    session_store = _get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, context_name
    )
    ann = session_store.load_annotation(annotation_id)
    if ann is None:
        logger.warning("404 annotation not found: id=%d", annotation_id)
        raise HTTPException(status_code=404, detail="Annotation not found")
    session_store.flag_annotation(annotation_id)
    return templates.TemplateResponse(
        request,
        "flagged.html",
        {"annotation_id": annotation_id},
    )
