import pytest

from core.models import Question
from core.question.generate_gemini import generate_question_gemini
from tests.fakes import FakeGeminiClient


@pytest.mark.asyncio
async def test_returns_question() -> None:
    expected = Question(text="What is the role of mitochondria?")
    client = FakeGeminiClient(parsed=expected)
    result = await generate_question_gemini("some prompt", client)
    assert result == expected


@pytest.mark.asyncio
async def test_passes_prompt_as_contents() -> None:
    client = FakeGeminiClient(parsed=Question(text="Some question?"))
    await generate_question_gemini("my prompt", client)
    assert client.aio.models.last_kwargs["contents"] == "my prompt"
    assert client.aio.models.last_kwargs["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_raises_when_parsed_is_none() -> None:
    client = FakeGeminiClient(parsed=None)
    with pytest.raises(ValueError, match="could not be parsed"):
        await generate_question_gemini("some prompt", client)
