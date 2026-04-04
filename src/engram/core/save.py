"""Save operation — store agent memory into the wiki."""

from __future__ import annotations

import logging

from engram.core.parsing import parse_article_response
from engram.llm.base import LLMClient
from engram.prompts import save as prompts
from engram.wiki.article import Article
from engram.wiki.store import WikiStore

logger = logging.getLogger(__name__)


def save_memory(
    memory: str,
    wiki: WikiStore,
    llm: LLMClient,
) -> tuple[Article, str]:
    """Save a piece of information into the wiki.

    Returns the article and a summary of what changed.
    """
    if not memory.strip():
        raise ValueError("Cannot save empty memory.")

    # Get current wiki state
    index_path = wiki.wiki_dir / "index.md"
    index_content = index_path.read_text() if index_path.exists() else "Wiki is empty."

    # Find relevant articles
    context = wiki.get_context_for_llm(memory)

    # Ask LLM to integrate the memory
    user_prompt = prompts.USER_TEMPLATE.format(
        memory=memory,
        index=index_content,
        articles=context,
    )

    response = llm.complete(
        system=prompts.SYSTEM,
        user=user_prompt,
    )

    # Parse and validate LLM response
    result = parse_article_response(response.content)

    # Create or update the article
    existing = wiki.get_article(result.slug)
    if existing and result.action == "update":
        existing.content = result.content
        existing.tags = result.tags
        wiki.save_article(existing)
        article = existing
    else:
        article = Article(
            slug=result.slug,
            title=result.title,
            content=result.content,
            tags=result.tags,
            sources=["agent-memory"],
        )
        wiki.save_article(article)

    wiki.append_log("save", f"{article.title}: {result.summary}")

    return article, result.summary
