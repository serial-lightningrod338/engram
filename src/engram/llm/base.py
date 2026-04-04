"""Abstract LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from an LLM call."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMClient(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> LLMResponse:
        """Send a completion request to the LLM."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name for logging."""
