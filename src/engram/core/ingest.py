"""Ingest operation — integrate external sources into the wiki."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from engram.core.parsing import parse_article_list_response
from engram.llm.base import LLMClient
from engram.prompts import ingest as prompts
from engram.sources.text import ParsedSource
from engram.wiki.article import Article
from engram.wiki.store import WikiStore

logger = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 30_000


def ingest_source(
    source: ParsedSource,
    wiki: WikiStore,
    llm: LLMClient,
    sources_dir: Path,
) -> list[tuple[Article, str]]:
    """Ingest an external source into the wiki.

    Returns list of (article, summary) tuples for each article created/updated.
    """
    # Save raw source
    _save_raw(source, sources_dir)

    # Get current wiki state
    index_path = wiki.wiki_dir / "index.md"
    index_content = index_path.read_text() if index_path.exists() else "Wiki is empty."

    # Find relevant articles
    context = wiki.get_context_for_llm(source.title or source.content[:200])

    # Truncate very long sources to fit context window
    content = source.content
    if len(content) > MAX_SOURCE_CHARS:
        content = content[:MAX_SOURCE_CHARS] + "\n\n[... content truncated for processing ...]"

    # Ask LLM to synthesize
    user_prompt = prompts.USER_TEMPLATE.format(
        origin=source.origin,
        source_type=source.source_type,
        content=content,
        index=index_content,
        articles=context,
    )

    response = llm.complete(
        system=prompts.SYSTEM,
        user=user_prompt,
        max_tokens=8192,
    )

    # Parse and validate LLM response
    results = parse_article_list_response(response.content)

    articles = []
    for result in results:
        existing = wiki.get_article(result.slug)
        if existing and result.action == "update":
            existing.content = result.content
            existing.tags = result.tags
            if source.origin not in existing.sources:
                existing.sources.append(source.origin)
            wiki.save_article(existing)
            article = existing
        else:
            article = Article(
                slug=result.slug,
                title=result.title,
                content=result.content,
                tags=result.tags,
                sources=[source.origin],
            )
            wiki.save_article(article)

        wiki.append_log("ingest", f"[{source.origin}] {article.title}: {result.summary}")
        articles.append((article, result.summary))

    return articles


def _save_raw(source: ParsedSource, sources_dir: Path) -> Path:
    """Save the raw source content to the sources directory."""
    sources_dir.mkdir(parents=True, exist_ok=True)

    # Find next sequence number safely (max of existing, not count)
    seqs = [
        int(m.group(1))
        for p in sources_dir.glob("*.md")
        if (m := re.match(r"^(\d+)_", p.name))
    ]
    seq = max(seqs, default=0) + 1

    slug = source.slug_hint
    filename = f"{seq:04d}_{slug}.md"
    path = sources_dir / filename

    header = f"# {source.title or source.origin}\n\n"
    header += f"**Source:** {source.origin}\n"
    header += f"**Type:** {source.source_type}\n\n---\n\n"

    path.write_text(header + source.content)
    return path
