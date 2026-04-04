"""Wiki store — manages the collection of articles and the index."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from engram.wiki.article import Article

logger = logging.getLogger(__name__)

SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9\-]{0,79}$")


class WikiStore:
    """Manages reading and writing articles to the wiki directory."""

    def __init__(self, wiki_dir: Path, log_path: Path) -> None:
        self.wiki_dir = wiki_dir
        self.log_path = log_path
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def _validate_slug(self, slug: str) -> None:
        """Validate slug is safe for filesystem use."""
        if not SAFE_SLUG.fullmatch(slug):
            raise ValueError(
                f"Invalid article slug: {slug!r}. "
                f"Must be lowercase alphanumeric with hyphens, 1-80 chars."
            )
        # Double-check no path traversal
        target = (self.wiki_dir / f"{slug}.md").resolve()
        if not str(target).startswith(str(self.wiki_dir.resolve())):
            raise ValueError(f"Slug would escape wiki directory: {slug!r}")

    def list_articles(self) -> list[Article]:
        """List all articles in the wiki."""
        articles = []
        for path in sorted(self.wiki_dir.glob("*.md")):
            if path.name == "index.md":
                continue
            try:
                articles.append(Article.load(path))
            except (OSError, ValueError) as exc:
                logger.warning("Skipping corrupted article %s: %s", path.name, exc)
                continue
        return articles

    def get_article(self, slug: str) -> Article | None:
        """Get a specific article by slug."""
        self._validate_slug(slug)
        path = self.wiki_dir / f"{slug}.md"
        if path.exists():
            return Article.load(path)
        return None

    def save_article(self, article: Article) -> Path:
        """Save an article and update the index."""
        self._validate_slug(article.slug)
        article.updated_at = datetime.now(timezone.utc)
        path = self.wiki_dir / article.filename
        path.write_text(article.to_markdown())
        self._rebuild_index()
        return path

    def delete_article(self, slug: str) -> bool:
        """Delete an article by slug."""
        self._validate_slug(slug)
        path = self.wiki_dir / f"{slug}.md"
        if path.exists():
            path.unlink()
            self._rebuild_index()
            return True
        return False

    def search(self, query: str) -> list[Article]:
        """Simple keyword search across all articles."""
        query_lower = query.lower()
        results = []
        for article in self.list_articles():
            score = 0
            if query_lower in article.title.lower():
                score += 3
            if any(query_lower in tag.lower() for tag in article.tags):
                score += 2
            if query_lower in article.content.lower():
                score += 1
            if score > 0:
                results.append((score, article))
        results.sort(key=lambda x: x[0], reverse=True)
        return [a for _, a in results]

    def append_log(self, action: str, details: str) -> None:
        """Append an entry to the chronological log."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        entry = f"- [{now}] **{action}**: {details}\n"
        with self.log_path.open("a") as f:
            f.write(entry)

    def _rebuild_index(self) -> None:
        """Rebuild the index.md file from all articles."""
        articles = self.list_articles()
        lines = ["# Engram Wiki Index", ""]

        tagged: dict[str, list[Article]] = {}
        untagged: list[Article] = []
        for article in articles:
            if article.tags:
                for tag in article.tags:
                    tagged.setdefault(tag, []).append(article)
            else:
                untagged.append(article)

        for tag in sorted(tagged.keys()):
            lines.append(f"## {tag.title()}")
            lines.append("")
            for article in tagged[tag]:
                lines.append(f"- [{article.title}]({article.filename})")
            lines.append("")

        if untagged:
            lines.append("## Uncategorized")
            lines.append("")
            for article in untagged:
                lines.append(f"- [{article.title}]({article.filename})")
            lines.append("")

        lines.append("---")
        lines.append(f"*{len(articles)} articles total*")
        lines.append("")

        index_path = self.wiki_dir / "index.md"
        index_path.write_text("\n".join(lines))

    def get_context_for_llm(self, query: str, max_articles: int = 5) -> str:
        """Build context string for LLM from relevant articles."""
        relevant = self.search(query)[:max_articles]
        if not relevant:
            all_articles = self.list_articles()
            all_articles.sort(key=lambda a: a.updated_at, reverse=True)
            relevant = all_articles[:max_articles]

        if not relevant:
            return "The wiki is empty. No articles exist yet."

        parts = ["## Relevant wiki articles:\n"]
        for article in relevant:
            parts.append(f"### {article.title} ({article.slug}.md)")
            parts.append(f"Tags: {', '.join(article.tags) if article.tags else 'none'}")
            parts.append(article.content)
            parts.append("")

        return "\n".join(parts)
