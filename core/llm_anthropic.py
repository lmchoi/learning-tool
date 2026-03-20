from typing import Any, TypeVar, cast

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

T = TypeVar("T")


class AnthropicAdapter:
    def __init__(self, client: AsyncAnthropic) -> None:
        self._client = client

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        output_type: type[T],
        model: str,
        max_tokens: int,
    ) -> T:
        response = await self._client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            messages=cast(list[MessageParam], messages),
            output_format=output_type,
        )
        if response.parsed_output is None:
            raise ValueError("LLM response could not be parsed into the expected type")
        return response.parsed_output
