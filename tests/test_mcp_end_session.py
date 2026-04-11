import pytest

from learning_tool.adapters.mcp.server import end_session, session_id


@pytest.mark.asyncio
async def test_end_session_returns_url() -> None:
    result = await end_session(context="biology")
    assert isinstance(result, str)
    assert f"/ui/biology/sessions/{session_id}" in result


@pytest.mark.asyncio
async def test_end_session_url_is_absolute() -> None:
    result = await end_session(context="biology")
    assert result.startswith("http")


@pytest.mark.asyncio
async def test_end_session_url_contains_context() -> None:
    result = await end_session(context="git")
    assert "/ui/git/sessions/" in result


@pytest.mark.asyncio
async def test_end_session_url_contains_session_id() -> None:
    result = await end_session(context="biology")
    assert session_id in result
