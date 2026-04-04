"""Source parsers for different input types."""

from engram.sources.text import parse_text
from engram.sources.url import fetch_url

__all__ = ["parse_text", "fetch_url"]
