from typing import Any, Protocol, cast

from core.models import Question

MODEL = "claude-haiku-4-5"


class AnthropicMessages(Protocol):
    async def parse(
        self, *, model: str, max_tokens: int, messages: Any, output_format: Any
    ) -> Any: ...


class AnthropicClient(Protocol):
    @property
    def messages(self) -> AnthropicMessages: ...


# Kept as the Anthropic-side concrete implementation alongside generate_gemini.py.
# Both are needed before extracting the LLMClient abstraction in #30.
async def generate_question(prompt: str, client: AnthropicClient) -> Question:
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=Question,
    )
    return cast(Question, response.parsed_output)
