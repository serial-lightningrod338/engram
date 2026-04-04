"""Tests for ingest operations."""

import json

from engram.core.ingest import _save_raw, ingest_source
from engram.sources.text import ParsedSource
from engram.wiki.store import WikiStore
from tests.helpers import MockLLMClient


class TestSaveRaw:
    def test_creates_file(self, tmp_engram) -> None:
        source = ParsedSource(
            content="Hello world.",
            source_type="text",
            origin="test-input",
            title="Test",
        )
        path = _save_raw(source, tmp_engram.sources_dir)
        assert path.exists()
        assert "0001_" in path.name

    def test_sequence_increments(self, tmp_engram) -> None:
        source = ParsedSource(
            content="Content.", source_type="text", origin="test", title="T",
        )
        p1 = _save_raw(source, tmp_engram.sources_dir)
        p2 = _save_raw(source, tmp_engram.sources_dir)
        assert "0001_" in p1.name
        assert "0002_" in p2.name


class TestIngestSource:
    def test_ingest_creates_article(
        self, wiki: WikiStore, mock_llm: MockLLMClient, tmp_engram,
    ) -> None:
        mock_llm.set_response(json.dumps([{
            "action": "create",
            "slug": "api-docs",
            "title": "API Documentation",
            "content": "The API uses REST endpoints.",
            "tags": ["api"],
            "summary": "Created API docs article.",
        }]))

        source = ParsedSource(
            content="REST API documentation...",
            source_type="url",
            origin="https://example.com/docs",
            title="API Docs",
        )

        results = ingest_source(source, wiki, mock_llm, tmp_engram.sources_dir)

        assert len(results) == 1
        article, summary = results[0]
        assert article.slug == "api-docs"
        assert "REST" in article.content

    def test_ingest_multiple_articles(
        self, wiki: WikiStore, mock_llm: MockLLMClient, tmp_engram,
    ) -> None:
        mock_llm.set_response(json.dumps([
            {
                "action": "create",
                "slug": "auth",
                "title": "Authentication",
                "content": "Uses OAuth2.",
                "tags": ["security"],
                "summary": "Auth article.",
            },
            {
                "action": "create",
                "slug": "rate-limits",
                "title": "Rate Limits",
                "content": "100 req/min.",
                "tags": ["api"],
                "summary": "Rate limit article.",
            },
        ]))

        source = ParsedSource(
            content="Docs about auth and rate limits.",
            source_type="url",
            origin="https://example.com",
            title="Docs",
        )

        results = ingest_source(source, wiki, mock_llm, tmp_engram.sources_dir)

        assert len(results) == 2
        slugs = {a.slug for a, _ in results}
        assert slugs == {"auth", "rate-limits"}
