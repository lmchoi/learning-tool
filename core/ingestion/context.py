import logging

from core.llm.constants import CONTEXT_EXTRACTION_MODEL
from core.llm.protocols import AnthropicClient
from core.models import ContextMetadata

logger = logging.getLogger(__name__)


async def extract_context(goal_text: str, client: AnthropicClient) -> ContextMetadata:
    logger.info("extracting context from GOAL.md")
    prompt = f"Extract the learner's goal and focus areas from the following text.\n\n{goal_text}"
    response = await client.messages.parse(
        model=CONTEXT_EXTRACTION_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
        output_format=ContextMetadata,
    )
    if response.parsed_output is None:
        logger.error("context extraction returned no structured output")
        raise ValueError("Context extraction returned no structured output")
    result: ContextMetadata = response.parsed_output
    logger.info(
        "context extraction complete: goal=%r focus_areas=%d", result.goal, len(result.focus_areas)
    )
    return result
