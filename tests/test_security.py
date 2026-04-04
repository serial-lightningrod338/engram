"""Security-focused tests."""

import pytest

from engram.wiki.store import WikiStore


class TestSlugValidation:
    def test_path_traversal_blocked(self, wiki: WikiStore):
        with pytest.raises(ValueError, match="Invalid article slug"):
            wiki._validate_slug("../../etc/passwd")

    def test_dotdot_blocked(self, wiki: WikiStore):
        with pytest.raises(ValueError, match="Invalid article slug"):
            wiki._validate_slug("..evil")

    def test_slash_blocked(self, wiki: WikiStore):
        with pytest.raises(ValueError, match="Invalid article slug"):
            wiki._validate_slug("path/traversal")

    def test_valid_slug_passes(self, wiki: WikiStore):
        wiki._validate_slug("valid-slug-123")  # Should not raise

    def test_uppercase_blocked(self, wiki: WikiStore):
        with pytest.raises(ValueError, match="Invalid article slug"):
            wiki._validate_slug("UpperCase")

    def test_empty_blocked(self, wiki: WikiStore):
        with pytest.raises(ValueError, match="Invalid article slug"):
            wiki._validate_slug("")


class TestSSRF:
    def test_private_ip_blocked(self):
        from engram.sources.url import _validate_url

        with pytest.raises(ValueError, match="blocked IP range"):
            _validate_url("http://127.0.0.1/evil")

    def test_metadata_ip_blocked(self):
        from engram.sources.url import _validate_url

        with pytest.raises(ValueError, match="blocked IP range"):
            _validate_url("http://169.254.169.254/latest/meta-data/")

    def test_file_scheme_blocked(self):
        from engram.sources.url import _validate_url

        with pytest.raises(ValueError, match="scheme not allowed"):
            _validate_url("file:///etc/passwd")

    def test_ftp_scheme_blocked(self):
        from engram.sources.url import _validate_url

        with pytest.raises(ValueError, match="scheme not allowed"):
            _validate_url("ftp://evil.com/file")


class TestAPIKeySecurity:
    def test_api_key_masked_in_repr(self):
        from pydantic import SecretStr

        from engram.config import LLMConfig

        config = LLMConfig(api_key=SecretStr("sk-secret-key-12345"))
        repr_str = repr(config)
        assert "sk-secret-key-12345" not in repr_str
        assert "***" in repr_str

    def test_api_key_not_in_toml(self, tmp_engram):
        """API keys must never be written to the config file."""
        config_text = tmp_engram.config_path.read_text()
        assert "api_key" not in config_text
