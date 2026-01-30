"""Tests unitaires pour les fonctions de recherche et URL."""

import json
from pathlib import Path

import pytest

from wakastart_leads.shared.utils.url_utils import normalize_url


# ===========================================================================
# Tests normalize_url (deja dans test_url.py mais aussi utilise ici)
# ===========================================================================


class TestNormalizeUrlBasic:
    """Tests basiques pour normalize_url."""

    def test_strips_https(self):
        assert normalize_url("https://example.com") == "example.com"

    def test_strips_http(self):
        assert normalize_url("http://example.com") == "example.com"

    def test_strips_www(self):
        assert normalize_url("https://www.example.com") == "example.com"


# ===========================================================================
# Tests pour les fonctions internes de main.py (si necessaires)
# Note: Les tests precedents utilisaient une API qui n'existe plus.
# Les fonctions load_search_criteria, format_search_criteria, et
# post_process_search_results sont maintenant des fonctions internes
# prefixees par _ dans main.py et utilisent des constantes de chemin.
# ===========================================================================
