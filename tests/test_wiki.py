"""Tests for the wiki store and article model."""

from engram.wiki.article import Article
from engram.wiki.store import WikiStore


class TestArticle:
    def test_roundtrip_markdown(self):
        article = Article(
            slug="test-article",
            title="Test Article",
            content="This is a test.\n\nWith multiple paragraphs.",
            tags=["testing", "demo"],
            sources=["manual"],
        )
        md = article.to_markdown()
        restored = Article.from_markdown(md, "test-article")

        assert restored.title == "Test Article"
        assert restored.slug == "test-article"
        assert "This is a test." in restored.content
        assert "testing" in restored.tags
        assert "demo" in restored.tags

    def test_slug_from_title(self):
        article = Article.from_markdown("No frontmatter here.", "my-cool-topic")
        assert article.title == "My Cool Topic"
        assert article.slug == "my-cool-topic"


class TestWikiStore:
    def test_save_and_list(self, wiki: WikiStore):
        article = Article(
            slug="first",
            title="First Article",
            content="Hello world.",
            tags=["test"],
        )
        wiki.save_article(article)

        articles = wiki.list_articles()
        assert len(articles) == 1
        assert articles[0].title == "First Article"

    def test_search(self, wiki: WikiStore):
        wiki.save_article(Article(
            slug="python-tips",
            title="Python Tips",
            content="Use list comprehensions for cleaner code.",
            tags=["python"],
        ))
        wiki.save_article(Article(
            slug="rust-tips",
            title="Rust Tips",
            content="Use pattern matching extensively.",
            tags=["rust"],
        ))

        results = wiki.search("python")
        assert len(results) >= 1
        assert results[0].slug == "python-tips"

    def test_delete(self, wiki: WikiStore):
        wiki.save_article(Article(
            slug="to-delete",
            title="Delete Me",
            content="Temporary.",
        ))
        assert wiki.get_article("to-delete") is not None

        wiki.delete_article("to-delete")
        assert wiki.get_article("to-delete") is None

    def test_index_rebuilt(self, wiki: WikiStore):
        wiki.save_article(Article(
            slug="indexed",
            title="Indexed Article",
            content="Content here.",
            tags=["demo"],
        ))
        index = (wiki.wiki_dir / "index.md").read_text()
        assert "Indexed Article" in index

    def test_append_log(self, wiki: WikiStore):
        wiki.append_log("test", "This is a test entry")
        log = wiki.log_path.read_text()
        assert "test" in log
        assert "This is a test entry" in log
