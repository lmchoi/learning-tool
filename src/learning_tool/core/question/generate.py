from typing import cast

from learning_tool.core.llm.constants import QUESTION_GENERATION_MODEL
from learning_tool.core.llm.protocols import AnthropicClient
from learning_tool.core.models import Question


# Kept as the Anthropic-side concrete implementation alongside generate_gemini.py.
# Both are needed before extracting the LLMClient abstraction in #30.
async def generate_question(prompt: str, client: AnthropicClient) -> Question:
    response = await client.messages.parse(
        model=QUESTION_GENERATION_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=Question,
    )
    return cast(Question, response.parsed_output)
