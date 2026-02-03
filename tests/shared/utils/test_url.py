"""Tests unitaires pour les fonctions URL dans shared/utils/url.py."""

from wakastart_leads.shared.utils.url_utils import normalize_url

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

    def test_already_normalized(self):
        assert normalize_url("example.com") == "example.com"

    def test_with_path(self):
        assert normalize_url("https://www.example.com/page") == "example.com/page"

    def test_all_combined(self):
        assert normalize_url("  HTTPS://WWW.Example.COM/  ") == "example.com"
