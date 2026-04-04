"""Article model — a single page in the wiki."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Article:
    """A wiki article stored as a markdown file."""

    slug: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def filename(self) -> str:
        return f"{self.slug}.md"

    def to_markdown(self) -> str:
        """Serialize article to markdown with YAML-like frontmatter."""
        lines = [
            "---",
            f"title: {self.title}",
            f"tags: {', '.join(self.tags)}",
            f"sources: {', '.join(self.sources)}",
            f"created: {self.created_at.isoformat()}",
            f"updated: {self.updated_at.isoformat()}",
            "---",
            "",
            self.content,
        ]
        return "\n".join(lines) + "\n"

    @classmethod
    def from_markdown(cls, text: str, slug: str) -> Article:
        """Parse an article from markdown with frontmatter."""
        frontmatter: dict[str, str] = {}
        content = text

        fm_match = re.match(r"^---\n(.+?)\n---\n\n?(.*)", text, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    frontmatter[key.strip()] = value.strip()
            content = fm_match.group(2)

        tags_str = frontmatter.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        sources_str = frontmatter.get("sources", "")
        sources = [s.strip() for s in sources_str.split(",") if s.strip()]

        created = datetime.now(timezone.utc)
        if "created" in frontmatter:
            try:
                created = datetime.fromisoformat(frontmatter["created"])
            except ValueError:
                pass

        updated = datetime.now(timezone.utc)
        if "updated" in frontmatter:
            try:
                updated = datetime.fromisoformat(frontmatter["updated"])
            except ValueError:
                pass

        return cls(
            slug=slug,
            title=frontmatter.get("title", slug.replace("-", " ").title()),
            content=content,
            tags=tags,
            sources=sources,
            created_at=created,
            updated_at=updated,
        )

    def save(self, wiki_dir: Path) -> Path:
        """Save article to disk."""
        path = wiki_dir / self.filename
        path.write_text(self.to_markdown())
        return path

    @classmethod
    def load(cls, path: Path) -> Article:
        """Load article from disk."""
        slug = path.stem
        return cls.from_markdown(path.read_text(), slug)
