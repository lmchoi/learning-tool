from typing import Any, Protocol, cast

from google.genai import types

from learning_tool.core.models import Question

MODEL = "gemini-2.5-flash"


class GeminiModels(Protocol):
    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any: ...


class GeminiAio(Protocol):
    @property
    def models(self) -> GeminiModels: ...


class GeminiClient(Protocol):
    @property
    def aio(self) -> GeminiAio: ...


async def generate_question_gemini(prompt: str, client: GeminiClient) -> Question:
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Question,
            max_output_tokens=1024,
        ),
    )
    if response.parsed is None:
        raise ValueError("Gemini response could not be parsed into the expected type")
    # cast needed: the SDK types response.parsed as Any even when response_schema is set
    return cast(Question, response.parsed)
