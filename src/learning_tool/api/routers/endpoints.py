import asyncio
import logging

from fastapi import APIRouter, HTTPException
from starlette.requests import Request

from learning_tool.api.deps import get_bank_store, get_session_store
from learning_tool.api.models import (
    AttemptRequest,
    EvaluateRequest,
    EvaluationResponse,
    QuestionResponse,
)
from learning_tool.core.context_name import validate_context_name
from learning_tool.core.evaluation.evaluate import evaluate_answer
from learning_tool.core.evaluation.prompt import build_evaluation_prompt
from learning_tool.core.models import UserProfile
from learning_tool.core.question.generate_gemini import generate_question_gemini
from learning_tool.core.question.prompt import build_question_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/contexts/{context_name}/questions", tags=["questions"])
async def get_bank_question(
    request: Request,
    context_name: str,
    pick: str | None = None,
    focus_area: str | None = None,
) -> dict[str, object]:
    if pick != "random":
        logger.warning("422 invalid pick param: %r", pick)
        raise HTTPException(status_code=422, detail="pick must be 'random'")
    bank_store = get_bank_store(
        request.app.state.bank_stores, request.app.state.store_dir, context_name
    )
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


@router.post("/api/attempts", tags=["attempts"], status_code=201)
async def post_attempt(request: Request, body: AttemptRequest) -> dict[str, int]:
    try:
        validate_context_name(body.context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not (request.app.state.store_dir / body.context).exists():
        logger.warning("404 context not found: %s", body.context)
        raise HTTPException(status_code=404, detail=f"Context '{body.context}' not found")
    session_store = get_session_store(
        request.app.state.session_stores, request.app.state.store_dir, body.context
    )
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


@router.get("/api/questions/{context}", tags=["questions"])
async def get_api_question(
    request: Request, context: str, focus_area: str | None = None
) -> dict[str, str]:
    try:
        validate_context_name(context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not (request.app.state.store_dir / context).exists():
        logger.warning("404 context not found: %s", context)
        raise HTTPException(status_code=404, detail=f"Context '{context}' not found")

    bank_store = get_bank_store(request.app.state.bank_stores, request.app.state.store_dir, context)
    question = await asyncio.to_thread(bank_store.get_random, focus_area)
    if question is None:
        logger.warning("404 question bank empty for context: %s", context)
        raise HTTPException(status_code=404, detail=f"No questions found for context '{context}'")

    return {
        "question_id": question.id,
        "question": question.question,
        "focus_area": question.focus_area,
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/contexts/{context_name}/question", tags=["questions"])
async def get_question(request: Request, context_name: str, query: str) -> QuestionResponse:
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
    return QuestionResponse(text=question.text, question_id=question.question_id)


@router.post("/contexts/{context_name}/evaluate", tags=["evaluation"])
async def post_evaluate(
    request: Request, context_name: str, body: EvaluateRequest
) -> EvaluationResponse:
    try:
        results = await asyncio.to_thread(
            request.app.state.retriever.retrieve, context_name, body.query, k=5
        )
        chunks = [chunk for chunk, _ in results]
    except FileNotFoundError as e:
        logger.warning("404 context not found: %s", context_name)
        raise HTTPException(status_code=404, detail=f"Context '{context_name}' not found") from e

    metadata = request.app.state.context_store.load_context(context_name)
    profile = UserProfile(experience_level="beginner")
    prompt = build_evaluation_prompt(
        question=body.question,
        answer=body.answer,
        chunks=chunks,
        profile=profile,
        metadata=metadata,
    )
    result = await evaluate_answer(prompt, request.app.state.anthropic)
    return EvaluationResponse(**result.model_dump())
