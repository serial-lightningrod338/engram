"""Lint operation — health check the wiki."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from engram.core.parsing import parse_lint_response
from engram.llm.base import LLMClient
from engram.prompts import lint as prompts
from engram.wiki.store import WikiStore

logger = logging.getLogger(__name__)

MAX_LINT_CHARS = 40_000


@dataclass
class LintIssue:
    """A single issue found during linting."""

    type: Literal[
        "contradiction", "stale", "missing_xref", "stub", "orphan", "duplicate"
    ]
    severity: Literal["high", "medium", "low"]
    articles: list[str]
    description: str
    suggestion: str


def lint_wiki(wiki: WikiStore, llm: LLMClient) -> list[LintIssue]:
    """Run a health check on the wiki.

    Returns a list of issues found.
    """
    articles = wiki.list_articles()
    if not articles:
        return []

    # Build full articles text
    parts = []
    for article in articles:
        parts.append(
            f"### {article.title} (slug: {article.slug})\n"
            f"Tags: {', '.join(article.tags) if article.tags else 'none'}\n"
            f"Sources: {', '.join(article.sources) if article.sources else 'none'}\n\n"
            f"{article.content}\n"
        )
    articles_text = "\n---\n\n".join(parts)

    if len(articles_text) > MAX_LINT_CHARS:
        articles_text = articles_text[:MAX_LINT_CHARS] + "\n\n[... truncated ...]"

    user_prompt = prompts.USER_TEMPLATE.format(articles=articles_text)

    response = llm.complete(
        system=prompts.SYSTEM,
        user=user_prompt,
    )

    # Parse and validate response
    results = parse_lint_response(response.content)

    issues = [
        LintIssue(
            type=r.type,
            severity=r.severity,
            articles=r.articles,
            description=r.description,
            suggestion=r.suggestion,
        )
        for r in results
    ]

    wiki.append_log("lint", f"Found {len(issues)} issues")

    return issues
