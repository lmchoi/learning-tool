from typing import cast

from learning_tool.core.llm.constants import ANSWER_EVALUATION_MODEL
from learning_tool.core.llm.protocols import AnthropicClient
from learning_tool.core.models import EvaluationResult


async def evaluate_answer(prompt: str, client: AnthropicClient) -> EvaluationResult:
    response = await client.messages.parse(
        model=ANSWER_EVALUATION_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=EvaluationResult,
    )
    return cast(EvaluationResult, response.parsed_output)
