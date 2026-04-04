"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from engram.config import CompressConfig, Config, LLMConfig
from engram.wiki.store import WikiStore
from tests.helpers import MockLLMClient


@pytest.fixture
def tmp_engram(tmp_path: Path) -> Config:
    """Create a temporary Engram configuration."""
    config = Config(
        home=tmp_path / ".engram",
        llm=LLMConfig(provider="ollama", model="mock"),
        compress=CompressConfig(max_hot_entries=5, max_hot_size_kb=10),
    )
    config.ensure_dirs()
    config.save()
    return config


@pytest.fixture
def wiki(tmp_engram: Config) -> WikiStore:
    """Create a temporary wiki store."""
    return WikiStore(tmp_engram.wiki_dir, tmp_engram.log_path)


@pytest.fixture
def mock_llm() -> MockLLMClient:
    """Create a mock LLM client."""
    return MockLLMClient()
