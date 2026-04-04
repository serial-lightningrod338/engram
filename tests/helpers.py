"""Shared test helpers — import from here, not conftest."""

from __future__ import annotations

from engram.llm.base import LLMClient, LLMResponse


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API calls."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = responses or []
        self._call_index = 0
        self.calls: list[tuple[str, str]] = []

    def set_response(self, response: str) -> None:
        self._responses = [response]
        self._call_index = 0

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        self.calls.append((system, user))
        if self._call_index < len(self._responses):
            content = self._responses[self._call_index]
            self._call_index += 1
        else:
            content = (
                '{"action": "create", "slug": "test", "title": "Test",'
                ' "content": "Test content.", "tags": ["test"],'
                ' "summary": "Test article created."}'
            )
        return LLMResponse(content=content, model="mock", input_tokens=10, output_tokens=20)

    @property
    def provider_name(self) -> str:
        return "mock"
