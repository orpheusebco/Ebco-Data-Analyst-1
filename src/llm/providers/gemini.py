from collections.abc import Iterator

from google import genai
from google.genai import types


class GeminiProvider:
    DEFAULT_MODEL = "gemini-2.5-pro"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL

    def _resolve(self, model: str | None) -> str:
        return model or self._model

    def call_model(
        self, prompt: str, *, system: str | None = None, model: str | None = None
    ) -> str:
        config = (
            types.GenerateContentConfig(system_instruction=system) if system else None
        )
        response = self._client.models.generate_content(
            model=self._resolve(model),
            contents=prompt,
            config=config,
        )
        return response.text or ""

    def stream_model(
        self, prompt: str, *, system: str | None = None, model: str | None = None
    ) -> Iterator[str]:
        config = (
            types.GenerateContentConfig(system_instruction=system) if system else None
        )
        for chunk in self._client.models.generate_content_stream(
            model=self._resolve(model),
            contents=prompt,
            config=config,
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield text
