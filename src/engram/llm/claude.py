"""Anthropic Claude LLM client."""

from __future__ import annotations

from engram.llm.base import LLMClient, LLMResponse


class ClaudeClient(LLMClient):
    """Claude client using the Anthropic SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for Claude. "
                "Install it with: pip install engram[claude]"
            ) from exc
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if not response.content:
            raise ValueError("Anthropic API returned an empty response.")
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    @property
    def provider_name(self) -> str:
        return "claude"
