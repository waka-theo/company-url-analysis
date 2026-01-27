"""Tests unitaires pour main.py (load_urls et post_process_csv)."""

import csv
import json
import os
from unittest.mock import patch

import pytest

import company_url_analysis_automation.main as main_module
from company_url_analysis_automation.main import load_urls, post_process_csv


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
# Tests post_process_csv
# ===========================================================================


class TestPostProcessCsv:
    """Tests pour la fonction post_process_csv."""

    def _make_csv_row(self, n_cols: int, prefix: str = "val") -> str:
        """Genere une ligne CSV avec n colonnes."""
        return ",".join(f"{prefix}{i}" for i in range(n_cols))

    def _setup_csv(self, tmp_path, content: str) -> str:
        """Cree un CSV dans tmp_path/output/test.csv, retourne le chemin absolu."""
        csv_file = tmp_path / "output" / "test.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        csv_file.write_text(content, encoding="utf-8")
        return str(csv_file)

    def test_valid_23_columns(self, tmp_path, monkeypatch):
        """Un CSV avec exactement 23 colonnes passe sans modification."""
        header = self._make_csv_row(23, prefix="header")
        row = self._make_csv_row(23, prefix="data")
        content = f"{header}\n{row}\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, "rb") as f:
            raw = f.read()
        assert raw[:3] == b"\xef\xbb\xbf"

    def test_pads_short_rows(self, tmp_path, monkeypatch):
        """Les lignes avec moins de 23 colonnes sont completees avec 'Non trouve'."""
        content = self._make_csv_row(20, prefix="data") + "\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert len(rows[0]) == 23
        assert rows[0][20] == "Non trouvé"
        assert rows[0][21] == "Non trouvé"
        assert rows[0][22] == "Non trouvé"

    def test_truncates_long_rows(self, tmp_path, monkeypatch):
        """Les lignes avec plus de 23 colonnes sont tronquees."""
        content = self._make_csv_row(25, prefix="data") + "\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert len(rows[0]) == 23

    def test_utf8_bom_encoding(self, tmp_path, monkeypatch):
        """Le fichier de sortie est encode en UTF-8 BOM."""
        content = self._make_csv_row(23) + "\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, "rb") as f:
            raw = f.read()
        assert raw[:3] == b"\xef\xbb\xbf"

    def test_strips_markdown_fences(self, tmp_path, monkeypatch):
        """Les code fences markdown sont supprimees."""
        row = self._make_csv_row(23)
        content = f"```csv\n{row}\n```\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, encoding="utf-8-sig") as f:
            content_out = f.read()
        assert "```" not in content_out

    def test_strips_empty_lines(self, tmp_path, monkeypatch):
        """Les lignes vides sont supprimees."""
        row = self._make_csv_row(23)
        content = f"{row}\n\n\n{row}\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 2

    def test_missing_file(self, tmp_path, monkeypatch, capsys):
        """Un fichier inexistant ne crash pas, print un warning."""
        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/inexistant.csv")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_empty_file(self, tmp_path, monkeypatch, capsys):
        """Un fichier vide ne crash pas, print un warning."""
        self._setup_csv(tmp_path, "")

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_preserves_data(self, tmp_path, monkeypatch):
        """Les donnees ne sont pas alterees par le post-processing."""
        values = [f"col{i}" for i in range(23)]
        content = ",".join(values) + "\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[0] == values

    def test_handles_commas_in_fields(self, tmp_path, monkeypatch):
        """Les virgules dans les champs quotes sont gerees correctement."""
        values = [f"col{i}" for i in range(22)] + ['"Strategie, angle"']
        content = ",".join(values) + "\n"
        full_path = self._setup_csv(tmp_path, content)

        monkeypatch.setattr(main_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv("output/test.csv")

        with open(full_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert len(rows[0]) == 23
