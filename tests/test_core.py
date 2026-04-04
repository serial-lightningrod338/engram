"""Tests for core operations."""

import json

from engram.core.query import query_wiki
from engram.core.save import save_memory
from engram.wiki.article import Article
from engram.wiki.store import WikiStore
from tests.helpers import MockLLMClient


class TestSave:
    def test_save_creates_article(self, wiki: WikiStore, mock_llm: MockLLMClient):
        mock_llm.set_response(json.dumps({
            "action": "create",
            "slug": "database-config",
            "title": "Database Configuration",
            "content": "Production DB is on port 5432.\n\nStaging DB is on port 5433.",
            "tags": ["infrastructure", "database"],
            "summary": "Created article about database configuration.",
        }))

        article, summary = save_memory(
            "The production database is on port 5432, staging is on 5433",
            wiki,
            mock_llm,
        )

        assert article.slug == "database-config"
        assert article.title == "Database Configuration"
        assert "5432" in article.content
        assert len(mock_llm.calls) == 1

    def test_save_updates_existing(self, wiki: WikiStore, mock_llm: MockLLMClient):
        # First save
        mock_llm.set_response(json.dumps({
            "action": "create",
            "slug": "api-limits",
            "title": "API Limits",
            "content": "Rate limit is 100 req/min.",
            "tags": ["api"],
            "summary": "Created.",
        }))
        save_memory("Rate limit is 100 req/min", wiki, mock_llm)

        # Second save — update
        mock_llm.set_response(json.dumps({
            "action": "update",
            "slug": "api-limits",
            "title": "API Limits",
            "content": "Rate limit is 100 req/min.\n\nBurst limit is 200 req/min.",
            "tags": ["api"],
            "summary": "Added burst limit info.",
        }))
        article, summary = save_memory("Burst limit is 200 req/min", wiki, mock_llm)

        assert "Burst limit" in article.content
        assert "Rate limit" in article.content

    def test_save_empty_memory_raises(self, wiki: WikiStore, mock_llm: MockLLMClient):
        import pytest
        with pytest.raises(ValueError, match="empty"):
            save_memory("", wiki, mock_llm)


class TestQuery:
    def test_query_returns_answer(self, wiki: WikiStore, mock_llm: MockLLMClient):
        wiki.save_article(Article(
            slug="ports",
            title="Port Configuration",
            content="Staging DB is on port 5433.",
            tags=["infra"],
        ))

        mock_llm.set_response("The staging database is on port 5433. (see: ports)")

        answer = query_wiki("what port is staging on?", wiki, mock_llm)

        assert "5433" in answer
        assert len(mock_llm.calls) == 1
