from typing import Any, Protocol


class AnthropicMessages(Protocol):
    async def parse(
        self, *, model: str, max_tokens: int, messages: Any, output_format: Any
    ) -> Any: ...


class AnthropicClient(Protocol):
    @property
    def messages(self) -> AnthropicMessages: ...
