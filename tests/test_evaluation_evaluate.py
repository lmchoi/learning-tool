from typing import Any

import pytest

from core.evaluation.evaluate import evaluate_answer
from core.models import EvaluationResult
from tests.fakes import FakeLLMClient


@pytest.mark.asyncio
async def test_returns_evaluation_result() -> None:
    expected = EvaluationResult(
        score=7,
        strengths=["Correct on energy production."],
        gaps=["Did not mention ATP."],
        missing_points=["ATP synthesis", "inner membrane"],
        suggested_addition="Mention the role of ATP synthase.",
        follow_up_question="How does the electron transport chain relate to ATP production?",
    )
    client = FakeLLMClient(output=expected)
    result = await evaluate_answer("some prompt", client)
    assert result == expected


@pytest.mark.asyncio
async def test_passes_prompt_as_user_message() -> None:
    client = FakeLLMClient(
        output=EvaluationResult(
            score=5,
            strengths=[],
            gaps=[],
            missing_points=[],
            suggested_addition=None,
            follow_up_question="",
        )
    )
    await evaluate_answer("my evaluation prompt", client)
    messages = client.last_kwargs["messages"]
    assert any(m["role"] == "user" and m["content"] == "my evaluation prompt" for m in messages)


@pytest.mark.asyncio
async def test_propagates_exceptions() -> None:
    class ErrorClient:
        async def complete(self, **kwargs: Any) -> Any:
            raise RuntimeError("API failure")

    with pytest.raises(RuntimeError, match="API failure"):
        await evaluate_answer("prompt", ErrorClient())
