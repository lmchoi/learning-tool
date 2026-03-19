from typing import Any, Protocol, cast

from core.models import Question

MODEL = "claude-sonnet-4-6"


class AnthropicMessages(Protocol):
    async def parse(
        self, *, model: str, max_tokens: int, messages: Any, output_format: Any
    ) -> Any: ...


class AnthropicClient(Protocol):
    @property
    def messages(self) -> AnthropicMessages: ...


async def generate_question(prompt: str, client: AnthropicClient) -> Question:
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=Question,
    )
    return cast(Question, response.parsed_output)
