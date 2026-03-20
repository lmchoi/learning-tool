import pytest

from core.models import Question
from core.question.generate import generate_question
from tests.fakes import FakeLLMClient


@pytest.mark.asyncio
async def test_returns_question() -> None:
    expected = Question(text="What is the role of mitochondria?")
    client = FakeLLMClient(output=expected)
    result = await generate_question("some prompt", client)
    assert result == expected


@pytest.mark.asyncio
async def test_passes_prompt_as_user_message() -> None:
    client = FakeLLMClient(output=Question(text="Some question?"))
    await generate_question("my prompt", client)
    messages = client.last_kwargs["messages"]
    assert any(m["role"] == "user" and m["content"] == "my prompt" for m in messages)
