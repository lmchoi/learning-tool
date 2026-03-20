import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from anthropic import AsyncAnthropic
from fastapi import FastAPI, HTTPException

from api.models import EvaluateRequest, EvaluationResponse
from core.evaluation.evaluate import evaluate_answer
from core.evaluation.prompt import build_evaluation_prompt
from core.ingestion.embedder import SentenceTransformerEmbedder
from core.ingestion.store import ChunkStore
from core.models import Question, UserProfile
from core.question.generate import generate_question
from core.question.prompt import build_question_prompt
from core.rag.retriever import Retriever


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    store_dir = Path(os.environ.get("STORE_DIR", "contexts/store"))
    embedder = SentenceTransformerEmbedder()
    store = ChunkStore(store_dir)
    app.state.retriever = Retriever(store=store, embedder=embedder)
    app.state.client = AsyncAnthropic()
    yield


app = FastAPI(lifespan=lifespan)


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
    return await generate_question(prompt, app.state.client)


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
    result = await evaluate_answer(prompt, app.state.client)
    return EvaluationResponse(**result.model_dump())
