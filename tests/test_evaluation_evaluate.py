import pytest

from core.evaluation.evaluate import evaluate_answer
from core.models import EvaluationResult
from tests.fakes import FakeAnthropicClient


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
    client = FakeAnthropicClient(parsed_output=expected)
    result = await evaluate_answer("some prompt", client)
    assert result == expected


@pytest.mark.asyncio
async def test_passes_prompt_as_user_message() -> None:
    client = FakeAnthropicClient(
        parsed_output=EvaluationResult(
            score=5,
            strengths=[],
            gaps=[],
            missing_points=[],
            suggested_addition=None,
            follow_up_question="",
        )
    )
    await evaluate_answer("my evaluation prompt", client)
    messages = client.messages.last_kwargs["messages"]
    assert any(m["role"] == "user" and m["content"] == "my evaluation prompt" for m in messages)


@pytest.mark.asyncio
async def test_propagates_exceptions() -> None:
    class ErrorMessages:
        async def parse(self, **kwargs: object) -> object:
            raise RuntimeError("API failure")

    class ErrorClient:
        @property
        def messages(self) -> ErrorMessages:
            return ErrorMessages()

    with pytest.raises(RuntimeError, match="API failure"):
        await evaluate_answer("prompt", ErrorClient())
