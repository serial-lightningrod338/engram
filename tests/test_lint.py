"""Tests for lint operations."""

import json

from engram.core.lint import lint_wiki
from engram.wiki.article import Article
from engram.wiki.store import WikiStore
from tests.helpers import MockLLMClient


class TestLintWiki:
    def test_empty_wiki(self, wiki: WikiStore, mock_llm: MockLLMClient) -> None:
        issues = lint_wiki(wiki, mock_llm)
        assert issues == []
        assert len(mock_llm.calls) == 0  # No LLM call for empty wiki

    def test_returns_issues(self, wiki: WikiStore, mock_llm: MockLLMClient) -> None:
        wiki.save_article(Article(
            slug="ports",
            title="Port Config",
            content="Staging is on port 5433.",
            tags=["infra"],
        ))

        mock_llm.set_response(json.dumps([{
            "type": "stub",
            "severity": "low",
            "articles": ["ports"],
            "description": "Article is very short.",
            "suggestion": "Add more details about production ports.",
        }]))

        issues = lint_wiki(wiki, mock_llm)

        assert len(issues) == 1
        assert issues[0].type == "stub"
        assert issues[0].severity == "low"
        assert "ports" in issues[0].articles

    def test_no_issues_found(self, wiki: WikiStore, mock_llm: MockLLMClient) -> None:
        wiki.save_article(Article(
            slug="complete-article",
            title="Complete Article",
            content="This is a thorough and well-written article with plenty of detail.",
            tags=["docs"],
        ))

        mock_llm.set_response("[]")

        issues = lint_wiki(wiki, mock_llm)
        assert issues == []
