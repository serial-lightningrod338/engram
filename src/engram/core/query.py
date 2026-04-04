"""Query operation — ask questions to the wiki."""

from __future__ import annotations

from engram.llm.base import LLMClient
from engram.prompts import query as prompts
from engram.wiki.store import WikiStore


def query_wiki(
    question: str,
    wiki: WikiStore,
    llm: LLMClient,
    max_articles: int = 10,
) -> str:
    """Query the wiki and return an answer.

    Returns the LLM's answer based on wiki content.
    """
    context = wiki.get_context_for_llm(question, max_articles=max_articles)

    user_prompt = prompts.USER_TEMPLATE.format(
        query=question,
        articles=context,
    )

    response = llm.complete(
        system=prompts.SYSTEM,
        user=user_prompt,
    )

    wiki.append_log("query", f"Q: {question[:80]}")

    return response.content
