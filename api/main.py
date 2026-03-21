import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from anthropic import AsyncAnthropic
from fastapi import FastAPI, Form, HTTPException
from fastapi.templating import Jinja2Templates
from google import genai
from starlette.requests import Request
from starlette.responses import HTMLResponse

from api.models import EvaluateRequest, EvaluationResponse
from core.evaluation.evaluate import evaluate_answer
from core.evaluation.prompt import build_evaluation_prompt
from core.ingestion.embedder import SentenceTransformerEmbedder
from core.ingestion.store import ChunkStore
from core.models import Question, UserProfile
from core.question.generate_gemini import generate_question_gemini
from core.question.prompt import build_question_prompt
from core.rag.retriever import Retriever
from core.session.store import SessionStore
from core.settings import STORE_DIR


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    store_dir = STORE_DIR
    embedder = SentenceTransformerEmbedder()
    store = ChunkStore(store_dir)
    app.state.retriever = Retriever(store=store, embedder=embedder)
    app.state.store_dir = store_dir
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is not set")
    app.state.anthropic = AsyncAnthropic()
    app.state.gemini = genai.Client()
    app.state.session_stores = {}  # dict[str, SessionStore], keyed by context name
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def _get_session_store(
    cache: dict[str, SessionStore], store_dir: Path, context: str
) -> SessionStore:
    if context not in cache:
        cache[context] = SessionStore(store_dir, context)
    return cache[context]


@app.get("/ui/{context_name}", response_class=HTMLResponse)
async def get_ui(request: Request, context_name: str, query: str) -> HTMLResponse:
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    session_id = session_store.start_session()
    return templates.TemplateResponse(
        request,
        "practice.html",
        {"context_name": context_name, "query": query, "session_id": session_id},
    )


@app.get("/ui/{context_name}/question", response_class=HTMLResponse)
async def get_question_fragment(
    request: Request, context_name: str, query: str, session_id: str
) -> HTMLResponse:
    try:
        results = await asyncio.to_thread(app.state.retriever.retrieve, context_name, query, k=5)
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile)
    question = await generate_question_gemini(prompt, app.state.gemini)
    return templates.TemplateResponse(
        request,
        "question.html",
        {
            "context_name": context_name,
            "question": question.text,
            "query": query,
            "session_id": session_id,
        },
    )


@app.post("/ui/{context_name}/evaluate", response_class=HTMLResponse)
async def post_evaluate_fragment(
    request: Request,
    context_name: str,
    question: str = Form(...),
    answer: str = Form(...),
    query: str = Form(...),
    session_id: str = Form(...),
) -> HTMLResponse:
    try:
        results = await asyncio.to_thread(app.state.retriever.retrieve, context_name, query, k=5)
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    profile = UserProfile(experience_level="beginner")
    prompt = build_evaluation_prompt(
        question=question, answer=answer, chunks=chunks, profile=profile
    )
    result = await evaluate_answer(prompt, app.state.anthropic)
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    attempt_id = session_store.record(session_id, question, answer, result.score)
    return templates.TemplateResponse(
        request,
        "feedback.html",
        {
            "context_name": context_name,
            "result": result,
            "session_id": session_id,
            "attempt_id": attempt_id,
        },
    )


@app.get("/annotate/form", response_class=HTMLResponse)
async def get_annotate_form(
    request: Request,
    attempt_id: int,
    context_name: str,
    sentiment: str,
) -> HTMLResponse:
    if sentiment not in ("up", "down"):
        raise HTTPException(status_code=422, detail="sentiment must be 'up' or 'down'")
    return templates.TemplateResponse(
        request,
        "annotation_form.html",
        {"attempt_id": attempt_id, "context_name": context_name, "sentiment": sentiment},
    )


@app.post("/annotate", response_class=HTMLResponse)
async def post_annotate(
    request: Request,
    attempt_id: int = Form(...),
    context_name: str = Form(...),
    sentiment: str = Form(...),
    comment: str | None = Form(default=None),
) -> HTMLResponse:
    if sentiment not in ("up", "down"):
        raise HTTPException(status_code=422, detail="sentiment must be 'up' or 'down'")
    session_store = _get_session_store(app.state.session_stores, app.state.store_dir, context_name)
    session_store.record_annotation(attempt_id, "question", sentiment, comment or None)
    return templates.TemplateResponse(
        request,
        "annotated.html",
        {"sentiment": sentiment},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/contexts/{context_name}/question")
async def get_question(context_name: str, query: str) -> Question:
    try:
        results = await asyncio.to_thread(app.state.retriever.retrieve, context_name, query, k=5)
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    profile = UserProfile(experience_level="beginner")
    prompt = build_question_prompt(chunks, profile)
    return await generate_question_gemini(prompt, app.state.gemini)


@app.post("/contexts/{context_name}/evaluate")
async def post_evaluate(context_name: str, body: EvaluateRequest) -> EvaluationResponse:
    try:
        results = await asyncio.to_thread(
            app.state.retriever.retrieve, context_name, body.query, k=5
        )
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    profile = UserProfile(experience_level="beginner")
    prompt = build_evaluation_prompt(
        question=body.question, answer=body.answer, chunks=chunks, profile=profile
    )
    result = await evaluate_answer(prompt, app.state.anthropic)
    return EvaluationResponse(**result.model_dump())
