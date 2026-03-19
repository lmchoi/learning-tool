from types import SimpleNamespace
from typing import Any

import pytest

from core.models import Question
from core.question.generate import generate_question


class FakeAnthropicMessages:
    def __init__(self, response_text: str) -> None:
        self._text = response_text
        self.last_kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(text=self._text)])


class FakeAnthropicClient:
    def __init__(self, response_text: str) -> None:
        self.messages = FakeAnthropicMessages(response_text)


@pytest.mark.asyncio
async def test_returns_question_with_response_text() -> None:
    client = FakeAnthropicClient("What is the role of mitochondria?")
    result = await generate_question("some prompt", client)
    assert result == Question(text="What is the role of mitochondria?")


@pytest.mark.asyncio
async def test_strips_whitespace_from_response() -> None:
    client = FakeAnthropicClient("  What is the role of mitochondria?  \n")
    result = await generate_question("some prompt", client)
    assert result == Question(text="What is the role of mitochondria?")


@pytest.mark.asyncio
async def test_passes_prompt_as_user_message() -> None:
    client = FakeAnthropicClient("Some question?")
    await generate_question("my prompt", client)
    messages = client.messages.last_kwargs["messages"]
    assert any(m["role"] == "user" and m["content"] == "my prompt" for m in messages)
