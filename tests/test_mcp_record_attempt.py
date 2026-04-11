import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from learning_tool.adapters.mcp.server import record_attempt, session_id


def test_session_id_is_uuid() -> None:
    """session_id should be a valid UUID string, stable for the process lifetime."""
    # Verify it's a valid UUID (won't raise if valid)
    uuid.UUID(session_id)


@pytest.fixture()
def mock_client() -> Generator[MagicMock]:
    with patch("httpx.AsyncClient") as MockClient:
        mock = MockClient.return_value
        mock.__aenter__.return_value = mock
        yield mock


@pytest.mark.asyncio
async def test_record_attempt_success(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"attempt_id": 99}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await record_attempt(
        context="biology",
        question_id="q-1",
        question="What is a cell?",
        answer="The smallest unit of life.",
        evaluation={"score": 8, "strengths": ["correct"], "gaps": []},
        score=8,
    )

    assert result == {"attempt_id": 99}


@pytest.mark.asyncio
async def test_record_attempt_sends_session_id(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"attempt_id": 1}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    await record_attempt(
        context="biology",
        question_id="q-1",
        question="What is a cell?",
        answer="The smallest unit of life.",
        evaluation={},
        score=5,
    )

    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert payload["session_id"] == session_id
    assert payload["context"] == "biology"
    assert payload["question_id"] == "q-1"
    assert payload["score"] == 5


@pytest.mark.asyncio
async def test_record_attempt_404_context_not_found(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock_response
    )
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await record_attempt(
        context="unknown",
        question_id="q-1",
        question="What?",
        answer="I dunno.",
        evaluation={},
        score=1,
    )

    assert isinstance(result, str)
    assert "Context 'unknown' not found" in result


@pytest.mark.asyncio
async def test_record_attempt_forwards_focus_area(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"attempt_id": 5}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    await record_attempt(
        context="biology",
        question_id="q-1",
        question="What is a cell?",
        answer="The smallest unit of life.",
        evaluation={"score": 8},
        score=8,
        focus_area="mitochondria",
    )

    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert payload["focus_area"] == "mitochondria"


@pytest.mark.asyncio
async def test_record_attempt_focus_area_none_when_not_passed(mock_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"attempt_id": 6}
    mock_response.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    await record_attempt(
        context="biology",
        question_id="q-1",
        question="What is a cell?",
        answer="The smallest unit of life.",
        evaluation={},
        score=5,
    )

    _, kwargs = mock_client.post.call_args
    payload = kwargs["json"]
    assert payload.get("focus_area") is None


@pytest.mark.asyncio
async def test_record_attempt_api_error(mock_client: MagicMock) -> None:
    mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

    result = await record_attempt(
        context="biology",
        question_id="q-1",
        question="What?",
        answer="I dunno.",
        evaluation={},
        score=1,
    )

    assert isinstance(result, str)
    assert "Error connecting to API" in result
