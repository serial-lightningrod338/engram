"""Compress operation — merge articles by topic to prevent unbounded growth."""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from engram.config import CompressConfig
from engram.llm.base import LLMClient
from engram.prompts import compress as prompts
from engram.wiki.article import Article
from engram.wiki.store import WikiStore

MAX_ARTICLE_SIZE = 200_000


def _tag_to_slug(tag: str) -> str:
    """Convert a tag name to a safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")
    return slug[:80] or "uncategorized"


def needs_compression(wiki: WikiStore, config: CompressConfig) -> bool:
    """Check if the wiki needs compression."""
    articles = wiki.list_articles()
    if len(articles) == 0:
        return False

    # Check total size
    total_size = sum(
        len(a.content.encode("utf-8")) for a in articles
    )
    total_kb = total_size / 1024

    # Check number of entries
    memory_marker = sum(1 for a in articles if "agent-memory" in a.sources)

    return memory_marker > config.max_hot_entries or total_kb > config.max_hot_size_kb


def compress_wiki(
    wiki: WikiStore,
    llm: LLMClient,
    config: CompressConfig,
) -> tuple[int, int]:
    """Compress wiki articles by merging and summarizing.

    Returns (articles_before, articles_after).
    """
    articles = wiki.list_articles()
    if not articles:
        return 0, 0

    articles_before = len(articles)

    # Backup before compressing
    _create_backup(wiki.wiki_dir)

    # Group articles by primary tag
    groups: dict[str, list[Article]] = {}
    for article in articles:
        key = article.tags[0] if article.tags else "uncategorized"
        groups.setdefault(key, []).append(article)

    # Compress each group that has multiple articles
    for tag, group_articles in groups.items():
        if len(group_articles) < 2:
            continue

        # Build entries text from all articles in group
        entries_parts = []
        for a in group_articles:
            entries_parts.append(f"## {a.title}\n\n{a.content}")
        entries_text = "\n\n---\n\n".join(entries_parts)

        user_prompt = prompts.USER_TEMPLATE.format(entries=entries_text)

        response = llm.complete(
            system=prompts.SYSTEM,
            user=user_prompt,
        )

        # Guard against empty or oversized LLM responses
        compressed_content = response.content.strip()
        if len(compressed_content) < 20:
            continue  # skip — don't destroy data with a bad response
        if len(compressed_content) > MAX_ARTICLE_SIZE:
            compressed_content = compressed_content[:MAX_ARTICLE_SIZE]

        # Create merged article
        merged = Article(
            slug=_tag_to_slug(tag),
            title=tag.title(),
            content=compressed_content,
            tags=[tag],
            sources=_merge_sources(group_articles),
            created_at=min(a.created_at for a in group_articles),
        )

        # Remove old articles
        for a in group_articles:
            wiki.delete_article(a.slug)

        # Save merged article
        wiki.save_article(merged)

    articles_after = len(wiki.list_articles())
    wiki.append_log(
        "compress",
        f"Compressed {articles_before} articles into {articles_after}",
    )

    return articles_before, articles_after


def _create_backup(wiki_dir: Path) -> Path:
    """Create a timestamped backup of the wiki."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = wiki_dir.parent / "backups" / timestamp
    shutil.copytree(wiki_dir, backup_dir)
    return backup_dir


def _merge_sources(articles: list[Article]) -> list[str]:
    """Merge and deduplicate sources from multiple articles."""
    seen: set[str] = set()
    sources: list[str] = []
    for a in articles:
        for s in a.sources:
            if s not in seen:
                seen.add(s)
                sources.append(s)
    return sources
