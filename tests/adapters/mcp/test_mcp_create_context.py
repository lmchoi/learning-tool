from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from learning_tool.adapters.mcp.server import create_context


@pytest.fixture()
def mock_client() -> Generator[MagicMock]:
    with patch("httpx.AsyncClient") as MockClient:
        mock = MockClient.return_value
        mock.__aenter__.return_value = mock
        yield mock


@pytest.mark.asyncio
async def test_create_context_success(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "draft_id": "d123",
        "review_url": "/ui/test-context/review/d123",
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await create_context(
        name="test-context", goal="Test goal", focus_areas=[{"name": "Area 1", "questions": ["Q1"]}]
    )

    assert "Draft created!" in result
    assert "/ui/test-context/review/d123" in result


@pytest.mark.asyncio
async def test_create_context_validation_error(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"detail": "Context name must be at least 4 characters"}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unprocessable Entity", request=MagicMock(), response=mock_response
    )
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await create_context(name="abc", goal="too short", focus_areas=[])

    assert "Validation error:" in result
    assert "at least 4 characters" in result


@pytest.mark.asyncio
async def test_create_context_api_error(mock_client: MagicMock) -> None:
    mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

    result = await create_context(name="test", goal="goal", focus_areas=[])

    assert "Error connecting to API" in result
