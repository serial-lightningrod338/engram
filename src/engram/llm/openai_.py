"""OpenAI LLM client."""

from __future__ import annotations

from engram.llm.base import LLMClient, LLMResponse


class OpenAIClient(LLMClient):
    """OpenAI client using the official SDK."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAI. "
                "Install it with: pip install engram[openai]"
            ) from exc
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=self.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )

    @property
    def provider_name(self) -> str:
        return "openai"
