"""Configuration management for Engram."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import toml
from pydantic import BaseModel, Field, SecretStr

DEFAULT_HOME = Path.home() / ".engram"

LLMProvider = Literal["claude", "openai", "ollama"]

VALID_PROVIDERS = ("claude", "openai", "ollama")


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: LLMProvider = "claude"
    model: str = "claude-sonnet-4-6"
    api_key: SecretStr = SecretStr("")
    base_url: str = ""  # For Ollama or custom endpoints

    def resolve_api_key(self) -> str:
        """Resolve API key from config or environment variables."""
        key = self.api_key.get_secret_value()
        if key:
            return key
        env_map = {
            "claude": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "ollama": "",
        }
        env_var = env_map.get(self.provider, "")
        if env_var:
            return os.environ.get(env_var, "")
        return ""

    def __repr__(self) -> str:
        return (
            f"LLMConfig(provider={self.provider!r}, model={self.model!r}, "
            f"api_key='***', base_url={self.base_url!r})"
        )


class CompressConfig(BaseModel):
    """Compression settings."""

    max_hot_entries: int = Field(default=50, description="Max entries before compressing")
    max_hot_size_kb: int = Field(default=200, description="Max KB in hot memory")
    summary_target_ratio: float = Field(default=0.3, description="Target compression ratio")


class Config(BaseModel):
    """Root configuration for Engram."""

    home: Path = DEFAULT_HOME
    llm: LLMConfig = Field(default_factory=LLMConfig)
    compress: CompressConfig = Field(default_factory=CompressConfig)

    @property
    def sources_dir(self) -> Path:
        return self.home / "sources" / "raw"

    @property
    def memory_dir(self) -> Path:
        return self.home / "memory"

    @property
    def wiki_dir(self) -> Path:
        return self.home / "wiki"

    @property
    def log_path(self) -> Path:
        return self.home / "log.md"

    @property
    def index_path(self) -> Path:
        return self.home / "wiki" / "index.md"

    @property
    def config_path(self) -> Path:
        return self.home / "engram.toml"

    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for d in [self.sources_dir, self.memory_dir, self.wiki_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save(self) -> None:
        """Save configuration to TOML file. API keys are NEVER persisted."""
        self.home.mkdir(parents=True, exist_ok=True)
        data = {
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "base_url": self.llm.base_url,
            },
            "compress": self.compress.model_dump(),
        }
        self.config_path.write_text(toml.dumps(data))

    @classmethod
    def load(cls, home: Path | None = None) -> Config:
        """Load configuration from TOML file, falling back to defaults."""
        home = home or DEFAULT_HOME
        config_path = home / "engram.toml"
        if config_path.exists():
            raw = toml.loads(config_path.read_text())
            llm_data = raw.get("llm", {})
            # Never load api_key from TOML — only from env vars
            llm_data.pop("api_key", None)
            compress_data = raw.get("compress", {})
            return cls(
                home=home,
                llm=LLMConfig(**llm_data),
                compress=CompressConfig(**compress_data),
            )
        return cls(home=home)
