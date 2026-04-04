"""Tests for compress operations."""

from engram.config import CompressConfig
from engram.core.compress import _tag_to_slug, compress_wiki, needs_compression
from engram.wiki.article import Article
from engram.wiki.store import WikiStore
from tests.helpers import MockLLMClient


class TestTagToSlug:
    def test_simple_tag(self) -> None:
        assert _tag_to_slug("database") == "database"

    def test_tag_with_spaces(self) -> None:
        assert _tag_to_slug("api reference") == "api-reference"

    def test_tag_with_special_chars(self) -> None:
        assert _tag_to_slug("C++") == "c"

    def test_uncategorized_fallback(self) -> None:
        assert _tag_to_slug("") == "uncategorized"

    def test_tag_with_mixed_case(self) -> None:
        assert _tag_to_slug("Infrastructure") == "infrastructure"


class TestNeedsCompression:
    def test_empty_wiki(self, wiki: WikiStore, tmp_engram) -> None:
        assert needs_compression(wiki, tmp_engram.compress) is False

    def test_below_threshold(self, wiki: WikiStore, tmp_engram) -> None:
        wiki.save_article(Article(
            slug="test",
            title="Test",
            content="Short content.",
            tags=["test"],
            sources=["agent-memory"],
        ))
        assert needs_compression(wiki, tmp_engram.compress) is False

    def test_above_entry_threshold(self, wiki: WikiStore) -> None:
        config = CompressConfig(max_hot_entries=2, max_hot_size_kb=1000)
        for i in range(3):
            wiki.save_article(Article(
                slug=f"test-{i}",
                title=f"Test {i}",
                content=f"Content {i}.",
                tags=["test"],
                sources=["agent-memory"],
            ))
        assert needs_compression(wiki, config) is True


class TestCompressWiki:
    def test_compress_merges_articles(self, wiki: WikiStore, mock_llm: MockLLMClient) -> None:
        # Create two articles with the same tag
        wiki.save_article(Article(
            slug="db-port",
            title="DB Port",
            content="Production DB is on port 5432.",
            tags=["infra"],
        ))
        wiki.save_article(Article(
            slug="db-staging",
            title="DB Staging",
            content="Staging DB is on port 5433.",
            tags=["infra"],
        ))

        mock_llm.set_response(
            "Production DB: port 5432. Staging DB: port 5433."
        )

        config = CompressConfig(max_hot_entries=1, max_hot_size_kb=1)
        before, after = compress_wiki(wiki, mock_llm, config)

        assert before == 2
        assert after == 1
        articles = wiki.list_articles()
        assert articles[0].slug == "infra"

    def test_compress_empty_wiki(self, wiki: WikiStore, mock_llm: MockLLMClient) -> None:
        config = CompressConfig()
        before, after = compress_wiki(wiki, mock_llm, config)
        assert before == 0
        assert after == 0

    def test_compress_untagged_articles(self, wiki: WikiStore, mock_llm: MockLLMClient) -> None:
        """Untagged articles should use 'uncategorized' slug, not crash."""
        wiki.save_article(Article(
            slug="note-a",
            title="Note A",
            content="First note.",
            tags=[],
        ))
        wiki.save_article(Article(
            slug="note-b",
            title="Note B",
            content="Second note.",
            tags=[],
        ))

        mock_llm.set_response("Combined notes: First and second.")

        config = CompressConfig()
        before, after = compress_wiki(wiki, mock_llm, config)

        assert before == 2
        assert after == 1
        articles = wiki.list_articles()
        assert articles[0].slug == "uncategorized"

    def test_compress_skips_short_response(self, wiki: WikiStore, mock_llm: MockLLMClient) -> None:
        """If LLM returns very short content, skip to avoid data loss."""
        wiki.save_article(Article(
            slug="a1", title="A1", content="Important data.", tags=["test"],
        ))
        wiki.save_article(Article(
            slug="a2", title="A2", content="More important data.", tags=["test"],
        ))

        mock_llm.set_response("Error")  # Too short — less than 20 chars

        config = CompressConfig()
        before, after = compress_wiki(wiki, mock_llm, config)

        # Articles should NOT be deleted since response was too short
        assert after == 2
