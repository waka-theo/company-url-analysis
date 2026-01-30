"""Tests unitaires pour main.py (load_urls, CLI functions)."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

import wakastart_leads.main as main_module
from wakastart_leads.main import (
    _setup_log_file,
    load_urls,
)


def _fake_file_path(tmp_path) -> str:
    """Retourne un chemin __file__ fictif 3 niveaux sous tmp_path.

    post_process_csv et load_urls font :
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    Avec __file__ = tmp_path/a/b/main.py, project_root resoudra vers tmp_path.
    """
    return str(tmp_path / "a" / "b" / "main.py")


# ===========================================================================
# Tests load_urls
# ===========================================================================


class TestLoadUrls:
    """Tests pour la fonction load_urls."""

    def test_test_mode(self, tmp_path, monkeypatch):
        """En mode test, charge liste_test.json."""
        urls = ["https://example.com", "https://test.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_urls(test_mode=True)
        assert result == urls

    def test_prod_mode(self, tmp_path, monkeypatch):
        """En mode prod, charge liste.json."""
        urls = ["https://prod1.com", "https://prod2.com"]
        prod_file = tmp_path / "liste.json"
        prod_file.write_text(json.dumps(urls), encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_urls(test_mode=False)
        assert result == urls

    def test_returns_list(self, tmp_path, monkeypatch):
        """Le resultat est une liste."""
        urls = ["https://example.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = load_urls(test_mode=True)
        assert isinstance(result, list)

    def test_file_not_found(self, tmp_path, monkeypatch):
        """Leve FileNotFoundError si le fichier n'existe pas."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        with pytest.raises(FileNotFoundError):
            load_urls(test_mode=True)


# ===========================================================================
# Tests _setup_log_file
# ===========================================================================


class TestSetupLogFile:
    """Tests pour la fonction _setup_log_file."""

    def test_creates_run_log_directory(self, tmp_path, monkeypatch):
        """Cree le dossier output/logs/run/."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        _setup_log_file("run")
        assert (tmp_path / "output" / "logs" / "run").is_dir()

    def test_creates_search_log_directory(self, tmp_path, monkeypatch):
        """Cree le dossier output/logs/search/."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        _setup_log_file("search")
        assert (tmp_path / "output" / "logs" / "search").is_dir()

    def test_returns_json_path(self, tmp_path, monkeypatch):
        """Retourne un chemin .json."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = _setup_log_file("run")
        assert result.endswith(".json")

    def test_path_contains_workflow_name(self, tmp_path, monkeypatch):
        """Le nom du fichier contient le nom du workflow."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = _setup_log_file("run")
        assert "run_" in os.path.basename(result)

    def test_path_contains_timestamp(self, tmp_path, monkeypatch):
        """Le nom du fichier contient un timestamp YYYYMMDD_HHMMSS."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = _setup_log_file("run")
        basename = os.path.basename(result)
        # Format: run_YYYYMMDD_HHMMSS.json
        parts = basename.replace(".json", "").split("_", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 15  # YYYYMMDD_HHMMSS

    def test_path_under_correct_subdirectory(self, tmp_path, monkeypatch):
        """Le fichier est dans output/logs/<workflow>/."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        result = _setup_log_file("search")
        expected_dir = str(tmp_path / "output" / "logs" / "search")
        assert os.path.dirname(result) == expected_dir

    def test_idempotent_directory_creation(self, tmp_path, monkeypatch):
        """Creer le dossier deux fois ne leve pas d'erreur."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        _setup_log_file("run")
        _setup_log_file("run")
        assert (tmp_path / "output" / "logs" / "run").is_dir()


# ===========================================================================
# Tests des fonctions CLI (run, train, replay, test)
# ===========================================================================


class TestRunFunction:
    """Tests pour la fonction run()."""

    def test_run_calls_crew_and_postprocess(self, tmp_path, monkeypatch):
        """run() charge les URLs, lance le crew, et post-process le CSV."""
        from wakastart_leads.main import run

        mock_crew_obj = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.crew.return_value = mock_crew_obj

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))

        urls = ["https://example.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        # Creer le log dir
        log_dir = tmp_path / "output" / "logs" / "run"
        log_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch(
                "wakastart_leads.main.AnalysisCrew",
                return_value=mock_crew_instance,
            ),
            patch("wakastart_leads.main.post_process_csv") as mock_pp,
        ):
            run()

        mock_crew_obj.kickoff.assert_called_once()
        mock_pp.assert_called_once()


class TestTrainFunction:
    """Tests pour la fonction train()."""

    def test_train_calls_crew(self, tmp_path, monkeypatch):
        from wakastart_leads.main import train

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        monkeypatch.setattr("sys.argv", ["main.py", "2", "output.json"])

        urls = ["https://example.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        mock_crew_obj = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.crew.return_value = mock_crew_obj

        with patch(
            "wakastart_leads.main.AnalysisCrew",
            return_value=mock_crew_instance,
        ):
            train()

        mock_crew_obj.train.assert_called_once()

    def test_train_wraps_exception(self, tmp_path, monkeypatch):
        from wakastart_leads.main import train

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        monkeypatch.setattr("sys.argv", ["main.py", "2", "output.json"])

        urls = ["https://example.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        mock_crew_obj = MagicMock()
        mock_crew_obj.train.side_effect = RuntimeError("train failed")
        mock_crew_instance = MagicMock()
        mock_crew_instance.crew.return_value = mock_crew_obj

        with (
            patch(
                "wakastart_leads.main.AnalysisCrew",
                return_value=mock_crew_instance,
            ),
            pytest.raises(Exception, match="training the crew"),
        ):
            train()


class TestReplayFunction:
    """Tests pour la fonction replay()."""

    def test_replay_calls_crew(self, monkeypatch):
        from wakastart_leads.main import replay

        monkeypatch.setattr("sys.argv", ["main.py", "task123"])

        mock_crew_obj = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.crew.return_value = mock_crew_obj

        with patch(
            "wakastart_leads.main.AnalysisCrew",
            return_value=mock_crew_instance,
        ):
            replay()

        mock_crew_obj.replay.assert_called_once_with(task_id="task123")

    def test_replay_wraps_exception(self, monkeypatch):
        from wakastart_leads.main import replay

        monkeypatch.setattr("sys.argv", ["main.py", "task123"])

        mock_crew_obj = MagicMock()
        mock_crew_obj.replay.side_effect = RuntimeError("replay failed")
        mock_crew_instance = MagicMock()
        mock_crew_instance.crew.return_value = mock_crew_obj

        with (
            patch(
                "wakastart_leads.main.AnalysisCrew",
                return_value=mock_crew_instance,
            ),
            pytest.raises(Exception, match="replaying the crew"),
        ):
            replay()


class TestTestFunction:
    """Tests pour la fonction test()."""

    def test_test_calls_crew(self, tmp_path, monkeypatch):
        from wakastart_leads.main import test

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        monkeypatch.setattr("sys.argv", ["main.py", "1", "gpt-4o"])

        urls = ["https://example.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        mock_crew_obj = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_instance.crew.return_value = mock_crew_obj

        with patch(
            "wakastart_leads.main.AnalysisCrew",
            return_value=mock_crew_instance,
        ):
            test()

        mock_crew_obj.test.assert_called_once()

    def test_test_wraps_exception(self, tmp_path, monkeypatch):
        from wakastart_leads.main import test

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        monkeypatch.setattr("sys.argv", ["main.py", "1", "gpt-4o"])

        urls = ["https://example.com"]
        test_file = tmp_path / "liste_test.json"
        test_file.write_text(json.dumps(urls), encoding="utf-8")

        mock_crew_obj = MagicMock()
        mock_crew_obj.test.side_effect = RuntimeError("test failed")
        mock_crew_instance = MagicMock()
        mock_crew_instance.crew.return_value = mock_crew_obj

        with (
            patch(
                "wakastart_leads.main.AnalysisCrew",
                return_value=mock_crew_instance,
            ),
            pytest.raises(Exception, match="testing the crew"),
        ):
            test()


# ===========================================================================
# Tests de la fonction search()
# ===========================================================================


class TestSearchFunction:
    """Tests pour la fonction search() du CLI."""

    def test_search_calls_crew_and_postprocess(self, tmp_path, monkeypatch):
        """search() charge les criteres, lance le crew, et post-process les resultats."""
        from wakastart_leads.main import search

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
                "wakastart_leads.main.SearchCrew",
                return_value=mock_search_instance,
            ),
            patch("wakastart_leads.main.post_process_search_results") as mock_pp,
        ):
            search()

        mock_crew_obj.kickoff.assert_called_once()
        mock_pp.assert_called_once()
