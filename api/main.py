import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import yaml
from anthropic import AsyncAnthropic
from fastapi import FastAPI, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from api.models import EvaluateRequest, EvaluationResponse, QuestionResponse
from core.context_import.parser import parse_import
from core.context_name import validate_context_name
from core.evaluation.evaluate import evaluate_answer
from core.evaluation.export_prompt import build_export_prompt
from core.evaluation.paste_back import parse_paste_back
from core.evaluation.prompt import build_evaluation_prompt
from core.ingestion.embedder import SentenceTransformerEmbedder
from core.ingestion.store import ChunkStore, ContextStore
from core.models import ContextMetadata, UserProfile
from core.question.generate_gemini import generate_question_gemini
from core.question.loader import load_questions
from core.question.prompt import build_question_prompt
from core.question.store import QuestionBankStore
from core.rag.retriever import Retriever
from core.session.store import SessionStore
from core.settings import GITHUB_REPO, GITHUB_TOKEN, LOG_LEVEL, STORE_DIR

logger = logging.getLogger(__name__)

_GITHUB_CONFIGURED = bool(GITHUB_TOKEN and GITHUB_REPO)
_IMPORT_PROMPT: str | None = None
_IMPORT_PROMPT_PATH = (
    Path(__file__).parent.parent / "core" / "context_import" / "context_import_prompt.md"
)


def _get_import_prompt() -> str:
    global _IMPORT_PROMPT
    if _IMPORT_PROMPT is None:
        _IMPORT_PROMPT = _IMPORT_PROMPT_PATH.read_text()
    return _IMPORT_PROMPT


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    store_dir = STORE_DIR
    logger.info("store dir: %s", store_dir)
    embedder = SentenceTransformerEmbedder()
    store = ChunkStore(store_dir)
    app.state.retriever = Retriever(store=store, embedder=embedder)
    logger.info("retriever ready")
    app.state.store_dir = store_dir
    app.state.context_store = ContextStore(store_dir)
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is not set")
    app.state.anthropic = AsyncAnthropic()
    logger.info("anthropic client ready")
    app.state.gemini = genai.Client()
    logger.info("gemini client ready")
    app.state.session_stores = {}  # dict[str, SessionStore], keyed by context name
    app.state.bank_stores = {}  # dict[str, QuestionBankStore], keyed by context name
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start
    logger.info("%s %s %s %.3fs", request.method, request.url.path, response.status_code, latency)
    return response


def _get_session_store(
    cache: dict[str, SessionStore], store_dir: Path, context: str
) -> SessionStore:
    if context not in cache:
        cache[context] = SessionStore(store_dir, context)
    return cache[context]


def _get_bank_store(
    cache: dict[str, QuestionBankStore], store_dir: Path, context: str
) -> QuestionBankStore:
    if context not in cache:
        cache[context] = QuestionBankStore(store_dir, context)
    return cache[context]


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def get_index(request: Request) -> HTMLResponse:
    store_dir: Path = request.app.state.store_dir
    contexts = (
        sorted(p.name for p in store_dir.iterdir() if p.is_dir()) if store_dir.exists() else []
    )
    return templates.TemplateResponse(request, "index.html", {"contexts": contexts})


@app.get("/ui/{context_name}", response_class=HTMLResponse, include_in_schema=False)
async def get_ui(request: Request, context_name: str, query: str | None = None) -> HTMLResponse:
    if query is None:
        metadata = app.state.context_store.load_context(context_name)
        if metadata is None:
            logger.warning("404 context not found: %s", context_name)
            raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found")
        return templates.TemplateResponse(
            request,
            "start.html",
            {"context_name": context_name, "focus_areas": metadata.focus_areas},
        )
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    session_id = session_store.start_session()
    return templates.TemplateResponse(
        request,
        "practice.html",
        {"context_name": context_name, "query": query, "session_id": session_id},
    )


@app.get("/ui/{context_name}/setup", response_class=HTMLResponse, include_in_schema=False)
async def get_setup(request: Request, context_name: str) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "setup.html",
        {"context_name": context_name, "prompt_text": _get_import_prompt()},
    )


@app.post("/ui/{context_name}/import", response_class=HTMLResponse, include_in_schema=False)
async def post_import(
    request: Request,
    context_name: str,
    chat_response: str = Form(...),
) -> HTMLResponse:
    try:
        imported = parse_import(chat_response)
    except ValueError as e:
        logger.warning("422 import parse error for context=%s: %s", context_name, e)
        raise HTTPException(status_code=422, detail=str(e)) from e

    logger.info(
        "import parsed: context=%s focus_areas=%d",
        context_name,
        len(imported.focus_areas),
    )
    return templates.TemplateResponse(
        request,
        "import_review.html",
        {
            "context_name": context_name,
            "goal": imported.goal,
            "focus_areas_questions": imported.questions,
        },
    )


@app.post("/ui/{context_name}/confirm", response_class=HTMLResponse, include_in_schema=False)
async def post_confirm(
    request: Request,
    context_name: str,
) -> HTMLResponse:
    form = await request.form()
    goal = str(form.get("goal", ""))
    focus_areas = [str(v) for v in form.getlist("focus_area")]

    if not goal:
        raise HTTPException(status_code=422, detail="goal is required")

    questions_by_area: list[tuple[str, list[str]]] = []
    for fa in focus_areas:
        raw_qs = [str(v) for v in form.getlist(f"question_{fa}")]
        qs = [q.strip() for q in raw_qs if q.strip()]
        if qs:
            questions_by_area.append((fa, qs))

    if not questions_by_area:
        raise HTTPException(status_code=422, detail="at least one question is required")

    metadata = ContextMetadata(
        goal=goal,
        focus_areas=[fa for fa, _ in questions_by_area],
    )
    await asyncio.to_thread(app.state.context_store.save_context, context_name, metadata)

    questions_data = [{"focus_area": fa, "questions": qs} for fa, qs in questions_by_area]
    questions_yaml = yaml.dump(questions_data, default_flow_style=False, allow_unicode=True)
    questions_path: Path = app.state.store_dir / context_name / "questions.yaml"
    await asyncio.to_thread(questions_path.write_text, questions_yaml)

    bank_store = _get_bank_store(app.state.bank_stores, app.state.store_dir, context_name)
    added = await asyncio.to_thread(bank_store.add, load_questions(questions_path))
    logger.info(
        "confirm complete: context=%s focus_areas=%d questions_added=%d",
        context_name,
        len(questions_by_area),
        added,
    )

    context_yaml = yaml.dump(metadata.model_dump(), default_flow_style=False, allow_unicode=True)
    return templates.TemplateResponse(
        request,
        "import_result.html",
        {
            "context_name": context_name,
            "context_yaml": context_yaml,
            "questions_yaml": questions_yaml,
        },
    )


@app.get("/ui/{context_name}/question", response_class=HTMLResponse, include_in_schema=False)
async def get_question_fragment(
    request: Request, context_name: str, query: str, session_id: str
) -> HTMLResponse:
    try:
        results = await asyncio.to_thread(app.state.retriever.retrieve, context_name, query, k=5)
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        logger.warning("404 context not found: %s", context_name)
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    metadata = app.state.context_store.load_context(context_name)
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile, metadata)
    question = await generate_question_gemini(prompt, app.state.gemini)
    return templates.TemplateResponse(
        request,
        "question.html",
        {
            "context_name": context_name,
            "question": question.text,
            "question_id": question.question_id,
            "query": query,
            "session_id": session_id,
        },
    )


@app.post("/ui/{context_name}/evaluate", response_class=HTMLResponse, include_in_schema=False)
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
        results = await asyncio.to_thread(app.state.retriever.retrieve, context_name, query, k=5)
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        logger.warning("404 context not found: %s", context_name)
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    metadata = app.state.context_store.load_context(context_name)
    profile = UserProfile(experience_level="beginner")
    prompt = build_evaluation_prompt(
        question=question, answer=answer, chunks=chunks, profile=profile, metadata=metadata
    )
    result = await evaluate_answer(prompt, app.state.anthropic)
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
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


@app.get("/ui/{context_name}/capture", response_class=HTMLResponse, include_in_schema=False)
async def get_capture(request: Request, context_name: str) -> HTMLResponse:
    try:
        validate_context_name(context_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    bank_store = _get_bank_store(app.state.bank_stores, app.state.store_dir, context_name)
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
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


@app.post("/ui/{context_name}/capture", response_class=HTMLResponse, include_in_schema=False)
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
    bank_store = _get_bank_store(app.state.bank_stores, app.state.store_dir, context_name)
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
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


@app.get("/ui/{context_name}/capture/export", response_class=HTMLResponse, include_in_schema=False)
async def get_capture_export(request: Request, context_name: str, session_id: str) -> HTMLResponse:
    try:
        validate_context_name(context_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    session, metadata = await asyncio.gather(
        asyncio.to_thread(session_store.load_session, session_id),
        asyncio.to_thread(app.state.context_store.load_context, context_name),
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


@app.post(
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
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)

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


@app.get("/ui/{context_name}/history", response_class=HTMLResponse, include_in_schema=False)
async def get_history(
    request: Request,
    context_name: str,
    matched: int | None = None,
    unmatched: str | None = None,
) -> HTMLResponse:
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    raw_sessions = session_store.load_sessions()
    sessions = []
    for s in reversed(raw_sessions):
        if not s.attempts:
            continue
        attempts = []
        for a in s.attempts:
            result = None
            if a.result_json:
                try:
                    result = json.loads(a.result_json)
                except json.JSONDecodeError:
                    logger.warning("malformed result_json for attempt in session %s", s.session_id)
            attempts.append({"attempt": a, "result": result})
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


@app.get("/annotate/form", response_class=HTMLResponse, include_in_schema=False)
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


@app.post("/annotate", response_class=HTMLResponse, include_in_schema=False)
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
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    session_store.record_annotation(question_id, "question", sentiment, comment or None)
    return templates.TemplateResponse(
        request,
        "annotated.html",
        {"sentiment": sentiment, "question_id": question_id, "context_name": context_name},
    )


@app.get("/report-evaluation/form", response_class=HTMLResponse, include_in_schema=False)
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


@app.post("/report-evaluation", response_class=HTMLResponse, include_in_schema=False)
async def post_report_evaluation(
    request: Request,
    question_id: str = Form(...),
    context_name: str = Form(...),
    comment: str = Form(...),
) -> HTMLResponse:
    if not comment.strip():
        logger.warning("422 empty comment on evaluation report for question_id=%s", question_id)
        raise HTTPException(status_code=422, detail="comment is required")
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    session_store.record_annotation(question_id, "evaluation", "down", comment)
    return templates.TemplateResponse(request, "evaluation_reported.html", {})


_VALID_TARGET_TYPES = {"question", "evaluation"}
_VALID_SENTIMENTS = {"up", "down"}


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def get_admin_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin_index.html")


@app.get("/admin/contexts", response_class=HTMLResponse, include_in_schema=False)
async def get_admin_contexts(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin_contexts.html", {"error": None})


@app.post(
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


@app.get("/admin/annotations", response_class=HTMLResponse, include_in_schema=False)
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
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
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


@app.post(
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
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    ann = session_store.load_annotation(annotation_id)
    if ann is None:
        logger.warning("404 annotation not found: id=%d", annotation_id)
        raise HTTPException(status_code=404, detail="Annotation not found")

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
    issue_url = resp.json().get("html_url", "")
    return templates.TemplateResponse(
        request,
        "escalated.html",
        {"issue_url": issue_url, "annotation_id": annotation_id},
    )


@app.post(
    "/admin/annotations/{annotation_id}/flag", response_class=HTMLResponse, include_in_schema=False
)
async def post_flag_annotation(
    request: Request,
    annotation_id: int,
    context_name: str,
) -> HTMLResponse:
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
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


@app.get("/contexts/{context_name}/questions", tags=["questions"])
async def get_bank_question(
    context_name: str,
    pick: str | None = None,
    focus_area: str | None = None,
) -> dict[str, object]:
    if pick != "random":
        logger.warning("422 invalid pick param: %r", pick)
        raise HTTPException(status_code=422, detail="pick must be 'random'")
    bank_store = _get_bank_store(app.state.bank_stores, app.state.store_dir, context_name)
    question = await asyncio.to_thread(bank_store.get_random, focus_area)
    if question is None:
        return {"question": None}
    return {
        "question": {
            "id": question.id,
            "focus_area": question.focus_area,
            "question": question.question,
        }
    }


@app.get("/ui/{context_name}/question/bank", response_class=HTMLResponse, include_in_schema=False)
async def get_bank_question_fragment(
    request: Request,
    context_name: str,
    focus_area: str,
    session_id: str,
) -> HTMLResponse:
    bank_store = _get_bank_store(app.state.bank_stores, app.state.store_dir, context_name)
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
        },
    )


@app.get("/api/questions/{context}", tags=["questions"])
async def get_api_question(context: str, focus_area: str | None = None) -> dict[str, str]:
    if not (app.state.store_dir / context).exists():
        logger.warning("404 context not found: %s", context)
        raise HTTPException(status_code=404, detail=f"Context '{context}' not found")

    bank_store = _get_bank_store(app.state.bank_stores, app.state.store_dir, context)
    question = await asyncio.to_thread(bank_store.get_random, focus_area)
    if question is None:
        logger.warning("404 question bank empty for context: %s", context)
        raise HTTPException(status_code=404, detail=f"No questions found for context '{context}'")

    return {
        "question_id": question.id,
        "question": question.question,
        "focus_area": question.focus_area,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/contexts/{context_name}/question", tags=["questions"])
async def get_question(context_name: str, query: str) -> QuestionResponse:
    try:
        results = await asyncio.to_thread(app.state.retriever.retrieve, context_name, query, k=5)
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        logger.warning("404 context not found: %s", context_name)
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    metadata = app.state.context_store.load_context(context_name)
    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile, metadata)
    question = await generate_question_gemini(prompt, app.state.gemini)
    return QuestionResponse(text=question.text, question_id=question.question_id)


@app.post("/contexts/{context_name}/evaluate", tags=["evaluation"])
async def post_evaluate(context_name: str, body: EvaluateRequest) -> EvaluationResponse:
    try:
        results = await asyncio.to_thread(
            app.state.retriever.retrieve, context_name, body.query, k=5
        )
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        logger.warning("404 context not found: %s", context_name)
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    metadata = app.state.context_store.load_context(context_name)
    profile = UserProfile(experience_level="beginner")
    prompt = build_evaluation_prompt(
        question=body.question,
        answer=body.answer,
        chunks=chunks,
        profile=profile,
        metadata=metadata,
    )
    result = await evaluate_answer(prompt, app.state.anthropic)
    return EvaluationResponse(**result.model_dump())
