from typing import Any


class FakeLLMClient:
    def __init__(self, output: Any) -> None:
        self._output = output
        self.last_kwargs: dict[str, Any] = {}

    async def complete(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return self._output
