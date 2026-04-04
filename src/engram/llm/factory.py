"""Factory for creating LLM clients from config."""

from __future__ import annotations

from engram.config import LLMConfig
from engram.llm.base import LLMClient


def create_client(config: LLMConfig) -> LLMClient:
    """Create an LLM client from configuration."""
    api_key = config.resolve_api_key()

    if config.provider == "claude":
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or run: engram config --provider claude --api-key <key>"
            )
        from engram.llm.claude import ClaudeClient

        return ClaudeClient(api_key=api_key, model=config.model)

    elif config.provider == "openai":
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or run: engram config --provider openai --api-key <key>"
            )
        from engram.llm.openai_ import OpenAIClient

        return OpenAIClient(api_key=api_key, model=config.model)

    elif config.provider == "ollama":
        from engram.llm.ollama import OllamaClient

        base_url = config.base_url or "http://localhost:11434"
        return OllamaClient(model=config.model, base_url=base_url)

    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")
