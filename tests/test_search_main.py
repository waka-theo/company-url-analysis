"""Tests unitaires pour les fonctions search de main.py."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

import company_url_analysis_automation.main as main_module
from company_url_analysis_automation.main import (
    format_search_criteria,
    load_search_criteria,
    normalize_url,
    post_process_search_results,
)


def _fake_file_path(tmp_path) -> str:
    """Retourne un chemin __file__ fictif 3 niveaux sous tmp_path.

    _get_project_root fait :
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    Avec __file__ = tmp_path/a/b/main.py, project_root resoudra vers tmp_path.
    """
    return str(tmp_path / "a" / "b" / "main.py")


# ===========================================================================
# Tests load_search_criteria
# ===========================================================================


class TestLoadSearchCriteria:
    """Tests pour la fonction load_search_criteria."""

    def test_loads_from_file(self, tmp_path, monkeypatch):
        """Charge correctement un fichier de criteres JSON."""
        criteria = {"keywords": ["SaaS"], "sector": "sante"}
        criteria_file = tmp_path / "search_criteria.json"
        criteria_file.write_text(json.dumps(criteria), encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_search_criteria()
        assert result == criteria

    def test_loads_from_custom_path(self, tmp_path, monkeypatch):
        """Charge depuis un chemin personnalise."""
        criteria = {"sector": "finance"}
        custom_file = tmp_path / "custom_criteria.json"
        custom_file.write_text(json.dumps(criteria), encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_search_criteria(str(custom_file))
        assert result == criteria

    def test_loads_from_relative_path(self, tmp_path, monkeypatch):
        """Charge depuis un chemin relatif (resolu par rapport a la racine du projet)."""
        criteria = {"keywords": ["ERP"]}
        criteria_file = tmp_path / "my_criteria.json"
        criteria_file.write_text(json.dumps(criteria), encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_search_criteria("my_criteria.json")
        assert result == criteria

    def test_file_not_found(self, tmp_path, monkeypatch):
        """Leve FileNotFoundError si le fichier n'existe pas."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        with pytest.raises(FileNotFoundError, match="Fichier de criteres non trouve"):
            load_search_criteria()

    def test_file_not_found_custom_path(self, tmp_path, monkeypatch):
        """Leve FileNotFoundError pour un chemin custom inexistant."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        with pytest.raises(FileNotFoundError):
            load_search_criteria("nonexistent.json")

    def test_all_fields(self, tmp_path, monkeypatch):
        """Charge tous les champs possibles."""
        criteria = {
            "keywords": ["SaaS sante", "CRM"],
            "sector": "sante",
            "geographic_zone": "France",
            "company_size": "startup",
            "creation_year_min": 2018,
            "creation_year_max": 2025,
            "max_results": 30,
            "naf_codes": ["6201Z", "6202A"],
            "exclude_domains": ["linkedin.com"],
        }
        criteria_file = tmp_path / "search_criteria.json"
        criteria_file.write_text(json.dumps(criteria), encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_search_criteria()
        assert result == criteria

    def test_empty_object(self, tmp_path, monkeypatch):
        """Un objet JSON vide est valide."""
        criteria_file = tmp_path / "search_criteria.json"
        criteria_file.write_text("{}", encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_search_criteria()
        assert result == {}

    def test_invalid_json(self, tmp_path, monkeypatch):
        """Leve une erreur sur un JSON invalide."""
        criteria_file = tmp_path / "search_criteria.json"
        criteria_file.write_text("not valid json", encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        with pytest.raises(json.JSONDecodeError):
            load_search_criteria()


# ===========================================================================
# Tests format_search_criteria
# ===========================================================================


class TestFormatSearchCriteria:
    """Tests pour la fonction format_search_criteria."""

    def test_keywords_list(self):
        """Formate une liste de mots-cles."""
        result = format_search_criteria({"keywords": ["SaaS", "CRM", "ERP"]})
        assert "Mots-cles: SaaS, CRM, ERP" in result

    def test_keywords_string(self):
        """Formate un mot-cle unique (string)."""
        result = format_search_criteria({"keywords": "SaaS sante"})
        assert "Mots-cles: SaaS sante" in result

    def test_sector(self):
        result = format_search_criteria({"sector": "sante"})
        assert "Secteur: sante" in result

    def test_geographic_zone(self):
        result = format_search_criteria({"geographic_zone": "France"})
        assert "Zone geographique: France" in result

    def test_company_size(self):
        result = format_search_criteria({"company_size": "startup"})
        assert "Taille entreprise: startup" in result

    def test_creation_year_min(self):
        result = format_search_criteria({"creation_year_min": 2018})
        assert "Annee creation min: 2018" in result

    def test_creation_year_max(self):
        result = format_search_criteria({"creation_year_max": 2025})
        assert "Annee creation max: 2025" in result

    def test_naf_codes(self):
        result = format_search_criteria({"naf_codes": ["6201Z", "6202A"]})
        assert "Codes NAF: 6201Z, 6202A" in result

    def test_exclude_domains(self):
        result = format_search_criteria({"exclude_domains": ["linkedin.com", "facebook.com"]})
        assert "Domaines exclus: linkedin.com, facebook.com" in result

    def test_empty_criteria(self):
        """Un dict vide retourne le message par defaut."""
        result = format_search_criteria({})
        assert "Aucun critere specifique" in result

    def test_all_criteria(self):
        """Tous les criteres sont formates."""
        criteria = {
            "keywords": ["SaaS sante"],
            "sector": "sante",
            "geographic_zone": "France",
            "company_size": "startup",
            "creation_year_min": 2018,
            "creation_year_max": 2025,
            "naf_codes": ["6201Z"],
            "exclude_domains": ["linkedin.com"],
        }
        result = format_search_criteria(criteria)
        assert "Mots-cles:" in result
        assert "Secteur:" in result
        assert "Zone geographique:" in result
        assert "Taille entreprise:" in result
        assert "Annee creation min:" in result
        assert "Annee creation max:" in result
        assert "Codes NAF:" in result
        assert "Domaines exclus:" in result

    def test_ignores_none_values(self):
        """Les valeurs None sont ignorees."""
        result = format_search_criteria({"sector": None, "keywords": ["SaaS"]})
        assert "Secteur" not in result
        assert "Mots-cles: SaaS" in result

    def test_ignores_empty_lists(self):
        """Les listes vides sont ignorees."""
        result = format_search_criteria({"keywords": [], "sector": "sante"})
        assert "Mots-cles" not in result
        assert "Secteur: sante" in result


# ===========================================================================
# Tests post_process_search_results
# ===========================================================================


class TestPostProcessSearchResults:
    """Tests pour la fonction post_process_search_results."""

    def _write_raw(self, tmp_path, content: str) -> None:
        """Ecrit le fichier brut dans output/search_results_raw.json."""
        raw_dir = tmp_path / "output"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "search_results_raw.json").write_text(content, encoding="utf-8")

    def test_parses_valid_json(self, tmp_path, monkeypatch):
        """Parse correctement un JSON array valide."""
        urls = ["https://example.com", "https://test.fr"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == urls

    def test_cleans_markdown_fences(self, tmp_path, monkeypatch):
        """Nettoie les code fences markdown."""
        content = '```json\n["https://example.com"]\n```'
        self._write_raw(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == ["https://example.com"]

    def test_normalizes_urls_adds_https(self, tmp_path, monkeypatch):
        """Ajoute https:// aux URLs sans protocole."""
        urls = ["example.com", "test.fr"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == ["https://example.com", "https://test.fr"]

    def test_deduplicates_http_vs_https(self, tmp_path, monkeypatch):
        """Deduplique http et https du meme domaine."""
        urls = ["https://example.com", "http://example.com"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert len(result) == 1

    def test_deduplicates_www(self, tmp_path, monkeypatch):
        """Deduplique www et non-www."""
        urls = ["https://www.example.com", "https://example.com"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert len(result) == 1

    def test_deduplicates_trailing_slash(self, tmp_path, monkeypatch):
        """Deduplique URLs avec et sans trailing slash."""
        urls = ["https://example.com/", "https://example.com"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert len(result) == 1

    def test_filters_empty_strings(self, tmp_path, monkeypatch):
        """Filtre les chaines vides."""
        urls = ["https://example.com", "", "  ", "https://test.fr"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert len(result) == 2

    def test_custom_output_path(self, tmp_path, monkeypatch):
        """Ecrit dans le fichier de sortie specifie."""
        urls = ["https://example.com"]
        self._write_raw(tmp_path, json.dumps(urls))
        output_path = str(tmp_path / "output" / "custom.json")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_search_results(final_output_path=output_path)

        assert os.path.exists(output_path)
        with open(output_path, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved == ["https://example.com"]

    def test_generates_timestamped_filename(self, tmp_path, monkeypatch):
        """Genere un nom de fichier avec timestamp quand aucun output n'est specifie."""
        urls = ["https://example.com"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_search_results(final_output_path=None)

        output_dir = tmp_path / "output"
        json_files = list(output_dir.glob("search_urls_*.json"))
        assert len(json_files) == 1

    def test_removes_raw_file(self, tmp_path, monkeypatch):
        """Supprime le fichier brut apres traitement."""
        urls = ["https://example.com"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )

        raw_path = tmp_path / "output" / "search_results_raw.json"
        assert not raw_path.exists()

    def test_handles_missing_raw_file(self, tmp_path, monkeypatch):
        """Retourne une liste vide si le fichier brut n'existe pas."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == []

    def test_handles_empty_raw_file(self, tmp_path, monkeypatch):
        """Retourne une liste vide si le fichier brut est vide."""
        self._write_raw(tmp_path, "")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == []

    def test_handles_invalid_json(self, tmp_path, monkeypatch):
        """Retourne une liste vide si le JSON est invalide."""
        self._write_raw(tmp_path, "not json at all")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == []

    def test_handles_non_array_json(self, tmp_path, monkeypatch):
        """Retourne une liste vide si le JSON n'est pas un array."""
        self._write_raw(tmp_path, '{"key": "value"}')

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == []

    def test_output_json_format_matches_liste_json(self, tmp_path, monkeypatch):
        """Le format de sortie est identique a liste.json (Array<string>)."""
        urls = ["https://example.com", "https://test.fr"]
        self._write_raw(tmp_path, json.dumps(urls))
        output_path = str(tmp_path / "output" / "result.json")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_search_results(final_output_path=output_path)

        with open(output_path, encoding="utf-8") as f:
            saved = json.load(f)

        assert isinstance(saved, list)
        assert all(isinstance(url, str) for url in saved)

    def test_skips_non_string_entries(self, tmp_path, monkeypatch):
        """Ignore les entrees non-string dans le JSON array."""
        self._write_raw(tmp_path, '["https://example.com", 42, null, true]')

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == ["https://example.com"]

    def test_preserves_url_order(self, tmp_path, monkeypatch):
        """Preserve l'ordre des URLs (Oui avant Probable dans la sortie de l'agent)."""
        urls = ["https://first.com", "https://second.fr", "https://third.io"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == urls

    def test_empty_after_markdown_cleanup(self, tmp_path, monkeypatch, capsys):
        """Un fichier brut ne contenant que des code fences retourne une liste vide."""
        self._write_raw(tmp_path, "```json\n```")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = post_process_search_results(
            final_output_path=str(tmp_path / "output" / "result.json"),
        )
        assert result == []

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_oserror_on_raw_delete(self, tmp_path, monkeypatch):
        """Un OSError lors de la suppression du fichier brut ne crash pas."""
        urls = ["https://example.com"]
        self._write_raw(tmp_path, json.dumps(urls))

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        with patch("os.remove", side_effect=OSError("permission denied")):
            result = post_process_search_results(
                final_output_path=str(tmp_path / "output" / "result.json"),
            )
        assert result == ["https://example.com"]


# ===========================================================================
# Tests de la fonction search()
# ===========================================================================


class TestSearchFunction:
    """Tests pour la fonction search() du CLI."""

    def test_search_calls_crew_and_postprocess(self, tmp_path, monkeypatch):
        """search() charge les criteres, lance le crew, et post-process les resultats."""
        from company_url_analysis_automation.main import search

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        monkeypatch.setattr("sys.argv", ["main.py", "search"])

        # Creer le fichier de criteres
        criteria = {"keywords": ["SaaS"], "max_results": 10}
        criteria_file = tmp_path / "search_criteria.json"
        criteria_file.write_text(json.dumps(criteria), encoding="utf-8")

        # Creer le log dir
        log_dir = tmp_path / "output" / "logs" / "search"
        log_dir.mkdir(parents=True, exist_ok=True)

        mock_crew_obj = MagicMock()
        mock_search_instance = MagicMock()
        mock_search_instance.crew.return_value = mock_crew_obj

        with (
            patch(
                "company_url_analysis_automation.main.SearchCrew",
                return_value=mock_search_instance,
            ),
            patch("company_url_analysis_automation.main.post_process_search_results") as mock_pp,
        ):
            search()

        mock_crew_obj.kickoff.assert_called_once()
        mock_pp.assert_called_once()
