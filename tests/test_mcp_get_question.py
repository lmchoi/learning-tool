from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from learning_tool.adapters.mcp.server import get_question


@pytest.fixture()
def mock_client() -> Generator[MagicMock]:
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.__aenter__.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_get_question_success(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "question_id": "q123",
        "question": "What is a cell?",
        "focus_area": "biology",
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await get_question("biology")
    assert result == {
        "question_id": "q123",
        "question": "What is a cell?",
        "focus_area": "biology",
    }


@pytest.mark.asyncio
async def test_get_question_with_focus_area(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "question_id": "q456",
        "question": "What is the powerhouse?",
        "focus_area": "mitochondria",
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await get_question("biology", focus_area="mitochondria")
    assert result == {
        "question_id": "q456",
        "question": "What is the powerhouse?",
        "focus_area": "mitochondria",
    }
    _, kwargs = mock_client.get.call_args
    assert kwargs["params"] == {"focus_area": "mitochondria"}


@pytest.mark.asyncio
async def test_get_question_not_found(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock_response
    )
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await get_question("unknown")
    assert isinstance(result, str)
    assert "Context 'unknown' not found" in result


@pytest.mark.asyncio
async def test_get_question_unexpected_response(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"wrong": "format"}
    mock_response.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    result = await get_question("biology")
    assert isinstance(result, str)
    assert "missing key" in result


@pytest.mark.asyncio
async def test_get_question_api_error(mock_client: MagicMock) -> None:
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

    result = await get_question("biology")
    assert isinstance(result, str)
    assert "Error connecting to API" in result
