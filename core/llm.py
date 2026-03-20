from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class LLMClient(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        output_type: type[T],
        model: str,
        max_tokens: int,
    ) -> T: ...
