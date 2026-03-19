from typing import Any, Protocol, cast

from core.models import EvaluationResult

MODEL = "claude-sonnet-4-6"


class AnthropicMessages(Protocol):
    async def parse(
        self, *, model: str, max_tokens: int, messages: Any, output_format: Any
    ) -> Any: ...


class AnthropicClient(Protocol):
    @property
    def messages(self) -> AnthropicMessages: ...


async def evaluate_answer(prompt: str, client: AnthropicClient) -> EvaluationResult:
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=EvaluationResult,
    )
    return cast(EvaluationResult, response.parsed_output)
