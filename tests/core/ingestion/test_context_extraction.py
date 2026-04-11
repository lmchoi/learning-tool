import pytest

from learning_tool.core.ingestion.context import extract_context
from learning_tool.core.models import ContextMetadata
from tests.fakes import FakeAnthropicClient


@pytest.mark.asyncio
async def test_returns_context_metadata() -> None:
    expected = ContextMetadata(
        goal="Preparing for a biology exam.",
        focus_areas=["cell biology", "genetics", "evolution"],
    )
    client = FakeAnthropicClient(parsed_output=expected)
    result = await extract_context("some goal text", client)
    assert result == expected


@pytest.mark.asyncio
async def test_passes_goal_text_in_user_message() -> None:
    client = FakeAnthropicClient(parsed_output=ContextMetadata(goal="g", focus_areas=["f"]))
    await extract_context("my goal description", client)
    messages = client.messages.last_kwargs["messages"]
    assert any(m["role"] == "user" and "my goal description" in m["content"] for m in messages)
