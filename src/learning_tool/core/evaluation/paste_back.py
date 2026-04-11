import json
import logging
import re

from learning_tool.core.models import EvaluationResult

logger = logging.getLogger(__name__)


def parse_paste_back(text: str) -> list[tuple[int, EvaluationResult]]:
    """
    Extract fenced JSON blocks from text.
    Each block must be a valid EvaluationResult plus an 'attempt_id'.
    Returns a list of (attempt_id, EvaluationResult).
    """
    pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
    blocks = pattern.findall(text)

    # Fallback to any JSON-looking block if no code blocks found.
    # NOTE: This non-greedy match works for current EvaluationResult but is fragile
    # if the LLM includes nested objects with braces.
    if not blocks:
        blocks = re.findall(r"(\{.*?\})", text, re.DOTALL)

    results = []
    for block in blocks:
        try:
            data = json.loads(block)
            if not isinstance(data, dict):
                logger.warning("skipping non-dict block: %r", block[:100])
                continue
            if "attempt_id" not in data:
                logger.warning("skipping block missing attempt_id: %r", block[:100])
                continue

            aid = int(data.pop("attempt_id"))
            # question_id might be present for LLM context, but we use aid for DB
            if "question_id" in data:
                data.pop("question_id")

            # The remaining data should match EvaluationResult
            eval_result = EvaluationResult(**data)
            results.append((aid, eval_result))
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning("failed to parse block: %s. Block: %r", e, block[:100])
    return results
