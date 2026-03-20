from core.llm import LLMClient
from core.models import EvaluationResult

MODEL = "claude-sonnet-4-6"


async def evaluate_answer(prompt: str, client: LLMClient) -> EvaluationResult:
    return await client.complete(
        messages=[{"role": "user", "content": prompt}],
        output_type=EvaluationResult,
        model=MODEL,
        max_tokens=1024,
    )
