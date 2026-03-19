from typing import Any

from core.models import Question

MODEL = "claude-sonnet-4-6"


async def generate_question(prompt: str, client: Any) -> Question:
    response = await client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return Question(text=response.content[0].text.strip())
