# ADR 005 — Hand-rolled fakes over unittest.mock for external clients

## Status
Accepted

## Context
Tests for code that calls external clients (Claude API, embedding models) need some
way to avoid hitting real services. The two main options are `unittest.mock` and
hand-rolled fake classes.

## Decision
Use hand-rolled fake classes, consistent with the existing `FakeEmbedder` pattern.

```python
class FakeAnthropicClient:
    def __init__(self, response_text: str) -> None:
        self.messages = FakeAnthropicMessages(response_text)

class FakeAnthropicMessages:
    def __init__(self, response_text: str) -> None:
        self._text = response_text

    async def create(self, **kwargs: Any) -> ...:
        return SimpleNamespace(content=[SimpleNamespace(text=self._text)])
```

## Why not unittest.mock

`unittest.mock` with `MagicMock` / `AsyncMock` works but has two problems:

- **Coupled to SDK internals.** The nested mock chain mirrors the SDK's response
  shape (`response.content[0].text`). If Anthropic changes the response object,
  tests break even if the production code adapts correctly.
- **Repeated setup.** The mock construction gets copy-pasted across tests, making
  the test suite harder to read and maintain.

## Why hand-rolled fakes

- **Explicit contract.** The fake documents exactly what shape the code depends on.
  If the SDK changes and the production code adapts, the fake breaks obviously —
  not silently.
- **Consistent with existing patterns.** `FakeEmbedder` already follows this
  approach. Keeping the pattern consistent makes the test suite easier to navigate.
- **Readable tests.** Tests pass a `FakeAnthropicClient("some response text")`
  with no setup boilerplate.

## Trade-offs
- Fakes need to be kept in sync with the real interface manually.
- For one-off tests, `unittest.mock` is less code. The fake pays off as the number
  of tests grows.

## Revisit if
The number of external clients grows significantly and maintaining fakes becomes
burdensome — at that point a shared `conftest.py` with reusable fakes or a
protocol-based injection approach may be worth considering.
