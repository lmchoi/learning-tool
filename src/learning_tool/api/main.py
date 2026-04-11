import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from anthropic import AsyncAnthropic
from fastapi import FastAPI, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from google import genai
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from learning_tool.api.deps import (
    _get_bank_store,
    _get_import_prompt,
    _get_session_store,
    templates,
)
from learning_tool.api.models import (
    DraftRequest,
    DraftResponse,
)
from learning_tool.api.routers import (  # noqa: F401 (used below)
    admin,
    annotations,
    api,
    capture,
    practice,
)
from learning_tool.core.context_import.draft_store import DraftStore
from learning_tool.core.context_import.parser import ImportedContext, parse_import
from learning_tool.core.context_name import validate_context_name
from learning_tool.core.ingestion.embedder import SentenceTransformerEmbedder
from learning_tool.core.ingestion.store import ChunkStore, ContextStore
from learning_tool.core.models import ContextMetadata
from learning_tool.core.question.loader import load_questions
from learning_tool.core.rag.retriever import Retriever
from learning_tool.core.settings import LOG_LEVEL, STORE_DIR

logger = logging.getLogger(__name__)


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
    app.state.draft_store = DraftStore(store_dir)
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
app.include_router(annotations.router)
app.include_router(admin.router)
app.include_router(capture.router)
app.include_router(api.router)
app.include_router(practice.router)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start
    logger.info("%s %s %s %.3fs", request.method, request.url.path, response.status_code, latency)
    return response


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def get_index(request: Request) -> HTMLResponse:
    store_dir: Path = request.app.state.store_dir
    context_store: ContextStore = request.app.state.context_store
    contexts: list[dict[str, str]] = []
    if store_dir.exists():
        names = sorted(p.name for p in store_dir.iterdir() if p.is_dir())
        metas = await asyncio.gather(
            *[asyncio.to_thread(context_store.load_context, name) for name in names]
        )
        contexts = [
            {"name": name, "goal": meta.goal}
            for name, meta in zip(names, metas, strict=True)
            if meta is not None and not meta.archived
        ]
    return templates.TemplateResponse(request, "index.html", {"contexts": contexts})


@app.get("/ui/_new-context-form", response_class=HTMLResponse, include_in_schema=False)
async def get_new_context_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "_new_context_form.html")


@app.post(
    "/ui/contexts/{context_name}/archive", response_class=HTMLResponse, include_in_schema=False
)
async def post_archive_context(request: Request, context_name: str) -> Response:
    context_store: ContextStore = request.app.state.context_store
    try:
        await asyncio.to_thread(context_store.archive_context, context_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(status_code=200)


@app.post("/ui/contexts", response_class=HTMLResponse, include_in_schema=False)
async def post_contexts(request: Request, name: str = Form(...)) -> HTMLResponse:
    try:
        validate_context_name(name)
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "_new_context_form.html",
            {"error": str(e)},
            status_code=400,
        )
    return HTMLResponse(headers={"HX-Redirect": f"/ui/{name}/setup"})


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


@app.post("/api/contexts/{context_name}/draft", response_model=DraftResponse)
async def create_draft(request: Request, context_name: str, body: DraftRequest) -> DraftResponse:
    try:
        validate_context_name(context_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    questions = [(fa.name, fa.questions) for fa in body.focus_areas]
    imported = ImportedContext(goal=body.goal, questions=questions)

    draft_id = app.state.draft_store.save(context_name, imported)
    review_url = f"/ui/{context_name}/review/{draft_id}"

    return DraftResponse(draft_id=draft_id, review_url=review_url)


@app.get(
    "/ui/{context_name}/review/{draft_id}", response_class=HTMLResponse, include_in_schema=False
)
async def get_review(request: Request, context_name: str, draft_id: str) -> HTMLResponse:
    imported = app.state.draft_store.load(context_name, draft_id)
    if not imported:
        raise HTTPException(status_code=404, detail="Draft not found")

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
