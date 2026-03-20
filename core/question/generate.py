from core.llm import LLMClient
from core.models import Question

MODEL = "claude-sonnet-4-6"


async def generate_question(prompt: str, client: LLMClient) -> Question:
    return await client.complete(
        messages=[{"role": "user", "content": prompt}],
        output_type=Question,
        model=MODEL,
        max_tokens=1024,
    )
