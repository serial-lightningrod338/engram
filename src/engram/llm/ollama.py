"""Ollama LLM client — free, local, private."""

from __future__ import annotations

import httpx

from engram.llm.base import LLMClient, LLMResponse


class OllamaClient(LLMClient):
    """Ollama client for local models. No API key needed."""

    def __init__(
        self,
        model: str = "llama3.1",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        content = data.get("message", {}).get("content", "")
        # Ollama doesn't always return token counts
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        return LLMResponse(
            content=content,
            model=self.model,
            input_tokens=prompt_eval_count,
            output_tokens=eval_count,
        )

    @property
    def provider_name(self) -> str:
        return "ollama"
