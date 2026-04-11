import asyncio
import json
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
from starlette.responses import HTMLResponse, RedirectResponse, Response

from learning_tool.api.deps import (
    _get_bank_store,
    _get_import_prompt,
    _get_session_store,
    templates,
)
from learning_tool.api.models import (
    AttemptRequest,
    DraftRequest,
    DraftResponse,
    EvaluateRequest,
    EvaluationResponse,
    QuestionResponse,
)
from learning_tool.api.routers import admin, annotations
from learning_tool.core.context_import.draft_store import DraftStore
from learning_tool.core.context_import.parser import ImportedContext, parse_import
from learning_tool.core.context_name import validate_context_name
from learning_tool.core.evaluation.evaluate import evaluate_answer
from learning_tool.core.evaluation.export_prompt import build_export_prompt
from learning_tool.core.evaluation.paste_back import parse_paste_back
from learning_tool.core.evaluation.prompt import build_evaluation_prompt
from learning_tool.core.ingestion.embedder import SentenceTransformerEmbedder
from learning_tool.core.ingestion.store import ChunkStore, ContextStore
from learning_tool.core.models import ContextMetadata, UserProfile
from learning_tool.core.question.generate_gemini import generate_question_gemini
from learning_tool.core.question.loader import load_questions
from learning_tool.core.question.prompt import build_question_prompt
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
            "form_action": f"/ui/{context_name}/evaluate",
            "skip_path": f"/ui/{context_name}/question",
            "skip_query_param": "query",
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


@app.post("/ui/{context_name}/submit", response_class=HTMLResponse, include_in_schema=False)
async def post_submit_fragment(
    request: Request,
    context_name: str,
    question: str = Form(...),
    answer: str = Form(...),
    query: str = Form(...),
    session_id: str = Form(...),
    question_id: str | None = Form(default=None),
) -> HTMLResponse:
    bank_store = _get_bank_store(app.state.bank_stores, app.state.store_dir, context_name)
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
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


@app.get(
    "/ui/{context_name}/sessions/{session_id}", response_class=HTMLResponse, include_in_schema=False
)
async def get_session_results(request: Request, context_name: str, session_id: str) -> HTMLResponse:
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    session = session_store.load_session(session_id)
    if session is None:
        return templates.TemplateResponse(
            request,
            "session.html",
            {"context_name": context_name, "session": None, "attempts": []},
            status_code=404,
        )
    attempts = []
    for a in session.attempts:
        result = None
        if a.result_json:
            try:
                result = json.loads(a.result_json)
                for _f in ("strengths", "gaps", "missing_points"):
                    if isinstance(result.get(_f), str):
                        result[_f] = [result[_f]]
            except json.JSONDecodeError:
                logger.warning("malformed result_json for attempt in session %s", session_id)
        attempts.append({"attempt": a, "result": result})
    return templates.TemplateResponse(
        request,
        "session.html",
        {"context_name": context_name, "session": session, "attempts": attempts},
    )


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
                    for _f in ("strengths", "gaps", "missing_points"):
                        if isinstance(result.get(_f), str):
                            result[_f] = [result[_f]]
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
            "form_action": f"/ui/{context_name}/submit",
            "skip_path": f"/ui/{context_name}/question/bank",
            "skip_query_param": "focus_area",
        },
    )


@app.post("/api/attempts", tags=["attempts"], status_code=201)
async def post_attempt(body: AttemptRequest) -> dict[str, int]:
    try:
        validate_context_name(body.context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not (app.state.store_dir / body.context).exists():
        logger.warning("404 context not found: %s", body.context)
        raise HTTPException(status_code=404, detail=f"Context '{body.context}' not found")
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, body.context)
    attempt_id = await asyncio.to_thread(
        session_store.record,
        body.session_id,
        body.question,
        body.answer,
        body.score,
        body.question_id,
        body.evaluation.model_dump_json(),
        focus_area=body.focus_area,
    )
    return {"attempt_id": attempt_id}


@app.get("/api/questions/{context}", tags=["questions"])
async def get_api_question(context: str, focus_area: str | None = None) -> dict[str, str]:
    try:
        validate_context_name(context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
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
