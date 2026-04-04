"""Tests for LLM response parsing and validation."""

import pytest

from engram.core.parsing import (
    ArticleResult,
    extract_json,
    parse_article_response,
    parse_lint_response,
)


class TestExtractJson:
    def test_plain_json(self):
        result = extract_json('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = extract_json(text)
        assert '"key"' in result

    def test_text_before_json(self):
        text = 'Here is the result:\n{"key": "value"}'
        result = extract_json(text)
        assert result == '{"key": "value"}'

    def test_array_extraction(self):
        text = 'Result: [{"a": 1}]'
        result = extract_json(text)
        assert result.startswith("[")


class TestArticleResult:
    def test_valid_slug(self):
        result = ArticleResult(
            action="create",
            slug="valid-slug-123",
            title="Test",
            content="Content here.",
        )
        assert result.slug == "valid-slug-123"

    def test_path_traversal_slug_rejected(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            ArticleResult(
                action="create",
                slug="../../etc/passwd",
                title="Evil",
                content="Hacked.",
            )

    def test_uppercase_slug_rejected(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            ArticleResult(
                action="create",
                slug="CamelCase",
                title="Bad",
                content="Nope.",
            )

    def test_empty_slug_rejected(self):
        with pytest.raises(ValueError):
            ArticleResult(
                action="create",
                slug="",
                title="Bad",
                content="Nope.",
            )

    def test_tags_validated(self):
        result = ArticleResult(
            action="create",
            slug="test",
            title="Test",
            content="Content.",
            tags=["valid", "  spaced  ", "also-valid"],
        )
        assert "valid" in result.tags
        assert "spaced" in result.tags
        assert "also-valid" in result.tags

    def test_invalid_action_rejected(self):
        with pytest.raises(ValueError):
            ArticleResult(
                action="delete",  # type: ignore[arg-type]
                slug="test",
                title="Test",
                content="Content.",
            )


class TestParseArticleResponse:
    def test_valid_json(self):
        text = (
            '{"action":"create","slug":"test","title":"Test",'
            '"content":"Hello.","summary":"Done."}'
        )
        result = parse_article_response(text)
        assert result.slug == "test"
        assert result.action == "create"

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            parse_article_response("This is not JSON at all.")

    def test_json_with_code_fence(self):
        text = '```json\n{"action":"create","slug":"test","title":"T","content":"C."}\n```'
        result = parse_article_response(text)
        assert result.slug == "test"


class TestParseLintResponse:
    def test_empty_array(self):
        result = parse_lint_response("[]")
        assert result == []

    def test_valid_issues(self):
        text = (
            '[{"type":"stub","severity":"low","articles":["a"],'
            '"description":"Too short","suggestion":"Expand"}]'
        )
        result = parse_lint_response(text)
        assert len(result) == 1
        assert result[0].type == "stub"
