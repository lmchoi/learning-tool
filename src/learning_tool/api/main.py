import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from anthropic import AsyncAnthropic
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from google import genai
from starlette.requests import Request
from starlette.responses import Response

from learning_tool.api.routers import (
    admin,
    annotations,
    capture,
    contexts,
    endpoints,
    practice,
)
from learning_tool.core.context_import.draft_store import DraftStore
from learning_tool.core.ingestion.embedder import SentenceTransformerEmbedder
from learning_tool.core.ingestion.store import ChunkStore, ContextStore
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
app.include_router(endpoints.router)
app.include_router(practice.router)
app.include_router(contexts.router)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start
    logger.info("%s %s %s %.3fs", request.method, request.url.path, response.status_code, latency)
    return response
