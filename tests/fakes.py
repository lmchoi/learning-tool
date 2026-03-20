from types import SimpleNamespace
from typing import Any


class FakeAnthropicMessages:
    def __init__(self, parsed_output: Any) -> None:
        self._parsed_output = parsed_output
        self.last_kwargs: dict[str, Any] = {}

    async def parse(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return SimpleNamespace(parsed_output=self._parsed_output)


class FakeAnthropicClient:
    def __init__(self, parsed_output: Any) -> None:
        self.messages = FakeAnthropicMessages(parsed_output)


class FakeGeminiModels:
    def __init__(self, parsed: Any) -> None:
        self._parsed = parsed
        self.last_kwargs: dict[str, Any] = {}

    async def generate_content(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return SimpleNamespace(parsed=self._parsed)


class FakeGeminiAio:
    def __init__(self, parsed: Any) -> None:
        self.models = FakeGeminiModels(parsed)


class FakeGeminiClient:
    def __init__(self, parsed: Any) -> None:
        self.aio = FakeGeminiAio(parsed)
