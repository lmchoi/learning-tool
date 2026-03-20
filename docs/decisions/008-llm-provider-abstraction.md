# ADR 008 — LLM Provider Abstraction

## Status
Accepted

## Decision

Introduce a thin `LLMClient` protocol in `core/` that decouples generation and evaluation logic from the Anthropic SDK. Implement an `AnthropicAdapter` that satisfies the protocol. No third-party abstraction library.

## The interface

```python
class LLMClient(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict],
        output_type: type[T],
        model: str,
        max_tokens: int,
    ) -> T: ...
```

`generate_question` and `evaluate_answer` depend only on `LLMClient`. The `AnthropicAdapter` wraps `AsyncAnthropic` and translates to its `.messages.parse(output_format=...)` API.

## Why not a library (LiteLLM, etc.)

LiteLLM is the common production answer — it provides a unified call across Anthropic, Gemini, OpenAI-compatible endpoints, etc. But:

- The OpenAI Python SDK cannot be used directly for Claude — Anthropic has its own SDK with a different interface.
- For a learning project, building the adapter pattern explicitly is more valuable than hiding it behind a dependency.
- Follows the project principle: don't add deps until there's a concrete reason.

If a second provider is ever actually needed in production use, switching to LiteLLM at that point is a one-adapter replacement, and by then the abstraction boundary will already be correct.

## Structured output

Structured output is the main provider-specific concern. Anthropic uses `.messages.parse(..., output_format=SomeModel)`. The adapter owns this translation — callers just pass `output_type=SomeModel`.

## Rejected alternatives

**LiteLLM (library):** Correct production answer, wrong for this project's learning goals and dep discipline.

**OpenAI SDK with base URL swap:** Doesn't work for Claude — Anthropic has its own SDK and API shape.

**Keep current Anthropic-shaped Protocol:** The existing `AnthropicClient` Protocol in `generate.py` and `evaluate.py` mirrors the Anthropic SDK directly. It's not reusable across providers and is duplicated across modules.
