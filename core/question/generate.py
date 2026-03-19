from typing import Any, cast

from core.models import Question

MODEL = "claude-sonnet-4-6"


async def generate_question(prompt: str, client: Any) -> Question:
    response = await client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=Question,
    )
    return cast(Question, response.parsed_output)
