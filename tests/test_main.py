"""Tests unitaires pour main.py et les utilitaires."""

import json

import pytest

from wakastart_leads.shared.utils import load_urls, normalize_url

# ===========================================================================
# Tests load_urls
# ===========================================================================


class TestLoadUrls:
    """Tests pour la fonction load_urls."""

    def test_test_mode(self, tmp_path):
        """En mode test, charge liste_test.json."""
        urls = ["https://example.com", "https://test.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        result = load_urls(tmp_path, test_mode=True)
        assert result == urls

    def test_prod_mode(self, tmp_path):
        """En mode prod, charge liste.json."""
        urls = ["https://prod1.com", "https://prod2.com"]
        prod_file = tmp_path / "liste.json"
        prod_file.write_text(json.dumps(urls), encoding="utf-8")

        result = load_urls(tmp_path, test_mode=False)
        assert result == urls

    def test_returns_list(self, tmp_path):
        """Le resultat est une liste."""
        urls = ["https://example.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        result = load_urls(tmp_path, test_mode=True)
        assert isinstance(result, list)

    def test_file_not_found(self, tmp_path):
        """Leve FileNotFoundError si le fichier n'existe pas."""
        with pytest.raises(FileNotFoundError):
            load_urls(tmp_path, test_mode=True)


# ===========================================================================
# Tests normalize_url
# ===========================================================================


class TestNormalizeUrl:
    """Tests pour la fonction normalize_url."""

    def test_strips_https(self):
        assert normalize_url("https://example.com") == "example.com"

    def test_strips_http(self):
        assert normalize_url("http://example.com") == "example.com"

    def test_strips_www(self):
        assert normalize_url("https://www.example.com") == "example.com"

    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/") == "example.com"

    def test_case_insensitive(self):
        assert normalize_url("https://Example.COM") == "example.com"

    def test_strips_whitespace(self):
        assert normalize_url("  https://example.com  ") == "example.com"

    def test_with_path(self):
        assert normalize_url("https://www.example.com/page") == "example.com/page"
