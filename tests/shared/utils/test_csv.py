"""Tests unitaires pour les fonctions CSV dans shared/utils/csv.py."""

import csv
import os
from unittest.mock import patch

import pytest

from wakastart_leads.shared.utils.csv import load_existing_csv, post_process_csv
import wakastart_leads.shared.utils.csv as csv_module


def _fake_file_path(tmp_path) -> str:
    """Retourne un chemin __file__ fictif 3 niveaux sous tmp_path.

    post_process_csv et load_existing_csv font :
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    Avec __file__ = tmp_path/a/b/csv.py, project_root resoudra vers tmp_path.
    """
    return str(tmp_path / "a" / "b" / "csv.py")


def _make_csv_row(n_cols: int, prefix: str = "val") -> list[str]:
    """Genere une liste de valeurs CSV avec n colonnes."""
    return [f"{prefix}{i}" for i in range(n_cols)]


def _write_csv(path: str, rows: list[list[str]], encoding: str = "utf-8") -> None:
    """Ecrit un CSV a partir d'une liste de lignes."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding=encoding, newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)


def _read_csv(path: str) -> list[list[str]]:
    """Lit un CSV et retourne toutes les lignes."""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.reader(f))


# ===========================================================================
# Tests load_existing_csv
# ===========================================================================


class TestLoadExistingCsv:
    """Tests pour la fonction load_existing_csv."""

    def test_file_not_found(self, tmp_path, monkeypatch):
        """Retourne (None, {}) si le fichier n'existe pas."""
        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        header, rows = load_existing_csv("output/nonexistent.csv")
        assert header is None
        assert rows == {}

    def test_empty_file(self, tmp_path, monkeypatch):
        """Retourne (None, {}) si le fichier est vide."""
        csv_file = tmp_path / "output" / "test.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        csv_file.write_text("", encoding="utf-8-sig")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        header, rows = load_existing_csv("output/test.csv")
        assert header is None
        assert rows == {}

    def test_loads_header_and_rows(self, tmp_path, monkeypatch):
        """Charge correctement le header et les lignes indexees par URL."""
        header = ["Societe", "Site Web"] + [f"col{i}" for i in range(2, 23)]
        row1 = ["Acme", "https://acme.com"] + [f"val{i}" for i in range(2, 23)]
        row2 = ["Beta", "https://beta.io"] + [f"val{i}" for i in range(2, 23)]

        csv_path = str(tmp_path / "output" / "test.csv")
        _write_csv(csv_path, [header, row1, row2], encoding="utf-8-sig")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        loaded_header, rows = load_existing_csv("output/test.csv")

        assert loaded_header == header
        assert len(rows) == 2
        assert "acme.com" in rows
        assert "beta.io" in rows

    def test_skips_rows_without_url(self, tmp_path, monkeypatch):
        """Ignore les lignes dont la colonne URL est vide."""
        header = ["Societe", "Site Web"] + [f"col{i}" for i in range(2, 23)]
        row_empty_url = ["Acme", ""] + [f"val{i}" for i in range(2, 23)]
        row_valid = ["Beta", "https://beta.io"] + [f"val{i}" for i in range(2, 23)]

        csv_path = str(tmp_path / "output" / "test.csv")
        _write_csv(csv_path, [header, row_empty_url, row_valid], encoding="utf-8-sig")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        _, rows = load_existing_csv("output/test.csv")

        assert len(rows) == 1
        assert "beta.io" in rows


# ===========================================================================
# Tests post_process_csv (incremental merge)
# ===========================================================================


class TestPostProcessCsv:
    """Tests pour la fonction post_process_csv (mode incremental)."""

    def _setup_new_csv(self, tmp_path, rows: list[list[str]]) -> None:
        """Cree le fichier new CSV dans tmp_path/output/company_report_new.csv."""
        csv_path = str(tmp_path / "output" / "company_report_new.csv")
        _write_csv(csv_path, rows)

    def _setup_existing_csv(self, tmp_path, rows: list[list[str]]) -> None:
        """Cree le fichier CSV existant dans tmp_path/output/company_report.csv."""
        csv_path = str(tmp_path / "output" / "company_report.csv")
        _write_csv(csv_path, rows, encoding="utf-8-sig")

    def _make_header(self) -> list[str]:
        return ["Societe", "Site Web"] + [f"col{i}" for i in range(2, 23)]

    def _make_row(self, name: str, url: str, prefix: str = "v") -> list[str]:
        return [name, url] + [f"{prefix}{i}" for i in range(2, 23)]

    def _final_csv_path(self, tmp_path) -> str:
        return str(tmp_path / "output" / "company_report.csv")

    # --- Premier run (pas de CSV existant) ---

    def test_first_run_creates_csv(self, tmp_path, monkeypatch):
        """Premier run sans CSV existant : cree le fichier correctement."""
        header = self._make_header()
        row = self._make_row("Acme", "https://acme.com")
        self._setup_new_csv(tmp_path, [header, row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows) == 2  # header + 1 data row
        assert rows[0] == header
        assert rows[1][0] == "Acme"

    # --- Merge avec nouvelles entrees ---

    def test_merge_appends_new_entries(self, tmp_path, monkeypatch):
        """Nouvelles URLs sont ajoutees au CSV existant."""
        header = self._make_header()
        existing_row = self._make_row("Acme", "https://acme.com", prefix="old")
        new_row = self._make_row("Beta", "https://beta.io", prefix="new")

        self._setup_existing_csv(tmp_path, [header, existing_row])
        self._setup_new_csv(tmp_path, [header, new_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows) == 3  # header + 2 data rows
        urls = {rows[i][1] for i in range(1, len(rows))}
        assert "https://acme.com" in urls
        assert "https://beta.io" in urls

    # --- Update (deduplication par URL) ---

    def test_merge_updates_existing_url(self, tmp_path, monkeypatch):
        """Une URL existante est mise a jour avec les nouvelles donnees."""
        header = self._make_header()
        existing_row = self._make_row("Acme Old", "https://acme.com", prefix="old")
        updated_row = self._make_row("Acme New", "https://acme.com", prefix="new")

        self._setup_existing_csv(tmp_path, [header, existing_row])
        self._setup_new_csv(tmp_path, [header, updated_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows) == 2  # header + 1 data row (pas de doublon)
        assert rows[1][0] == "Acme New"
        assert rows[1][2] == "new2"

    def test_merge_normalizes_urls_for_dedup(self, tmp_path, monkeypatch):
        """http vs https, www, trailing slash sont normalises pour la dedup."""
        header = self._make_header()
        existing_row = self._make_row("Acme", "https://www.acme.com/", prefix="old")
        updated_row = self._make_row("Acme Updated", "http://acme.com", prefix="new")

        self._setup_existing_csv(tmp_path, [header, existing_row])
        self._setup_new_csv(tmp_path, [header, updated_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows) == 2  # header + 1 (pas de doublon)
        assert rows[1][0] == "Acme Updated"

    # --- Header unique ---

    def test_single_header_row(self, tmp_path, monkeypatch):
        """Le fichier final n'a qu'un seul header, meme apres merge."""
        header = self._make_header()
        existing_row = self._make_row("Acme", "https://acme.com")
        new_row = self._make_row("Beta", "https://beta.io")

        self._setup_existing_csv(tmp_path, [header, existing_row])
        self._setup_new_csv(tmp_path, [header, new_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        # Seul le premier row est un header
        assert rows[0] == header
        # Les lignes suivantes ne sont pas des headers
        for row in rows[1:]:
            assert row != header

    # --- UTF-8 BOM ---

    def test_utf8_bom_after_merge(self, tmp_path, monkeypatch):
        """Le fichier final est encode en UTF-8 BOM apres merge."""
        header = self._make_header()
        row = self._make_row("Acme", "https://acme.com")
        self._setup_new_csv(tmp_path, [header, row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        with open(self._final_csv_path(tmp_path), "rb") as f:
            raw = f.read()
        assert raw[:3] == b"\xef\xbb\xbf"

    # --- Suppression fichier temporaire ---

    def test_temp_file_deleted(self, tmp_path, monkeypatch):
        """Le fichier temporaire est supprime apres merge."""
        header = self._make_header()
        row = self._make_row("Acme", "https://acme.com")
        self._setup_new_csv(tmp_path, [header, row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        temp_path = str(tmp_path / "output" / "company_report_new.csv")
        assert not os.path.exists(temp_path)

    # --- Backup ---

    def test_backup_created(self, tmp_path, monkeypatch):
        """Un backup est cree dans output/backups/ quand un CSV existant a des donnees."""
        header = self._make_header()
        existing_row = self._make_row("Acme", "https://acme.com")
        new_row = self._make_row("Beta", "https://beta.io")

        self._setup_existing_csv(tmp_path, [header, existing_row])
        self._setup_new_csv(tmp_path, [header, new_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        backup_dir = tmp_path / "output" / "backups"
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob("company_report_*.csv"))
        assert len(backup_files) == 1

    def test_no_backup_on_first_run(self, tmp_path, monkeypatch):
        """Pas de backup quand il n'y a pas de CSV existant."""
        header = self._make_header()
        row = self._make_row("Acme", "https://acme.com")
        self._setup_new_csv(tmp_path, [header, row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        backup_dir = tmp_path / "output" / "backups"
        assert not backup_dir.exists()

    # --- Validation colonnes ---

    def test_pads_short_rows(self, tmp_path, monkeypatch):
        """Les lignes avec moins de 23 colonnes sont completees."""
        header = self._make_header()
        short_row = ["Acme", "https://acme.com"] + [f"v{i}" for i in range(2, 18)]  # 18 cols
        self._setup_new_csv(tmp_path, [header, short_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows[1]) == 23
        assert rows[1][18] == "Non trouve"

    def test_truncates_long_rows(self, tmp_path, monkeypatch):
        """Les lignes avec plus de 23 colonnes sont tronquees."""
        header = self._make_header()
        long_row = ["Acme", "https://acme.com"] + [f"v{i}" for i in range(2, 26)]  # 26 cols
        self._setup_new_csv(tmp_path, [header, long_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows[1]) == 23

    # --- Nettoyage markdown ---

    def test_strips_markdown_fences(self, tmp_path, monkeypatch):
        """Les code fences markdown sont supprimees."""
        header = self._make_header()
        row = self._make_row("Acme", "https://acme.com")
        content = "```csv\n" + ",".join(header) + "\n" + ",".join(row) + "\n```\n"

        csv_path = tmp_path / "output" / "company_report_new.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(content, encoding="utf-8")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        with open(self._final_csv_path(tmp_path), encoding="utf-8-sig") as f:
            content_out = f.read()
        assert "```" not in content_out

    # --- Warnings ---

    def test_missing_new_csv(self, tmp_path, monkeypatch, capsys):
        """Un fichier new CSV inexistant ne crash pas, print un warning."""
        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/nonexistent.csv",
            final_csv_path="output/company_report.csv",
        )

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_empty_new_csv(self, tmp_path, monkeypatch, capsys):
        """Un fichier new CSV vide ne crash pas, print un warning."""
        csv_path = tmp_path / "output" / "company_report_new.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text("", encoding="utf-8")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    # --- Donnees preservees ---

    def test_preserves_existing_data_on_merge(self, tmp_path, monkeypatch):
        """Les donnees existantes sont preservees apres un merge."""
        header = self._make_header()
        existing_row = self._make_row("Acme", "https://acme.com", prefix="existing")
        new_row = self._make_row("Beta", "https://beta.io", prefix="new")

        self._setup_existing_csv(tmp_path, [header, existing_row])
        self._setup_new_csv(tmp_path, [header, new_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        data_rows = rows[1:]
        acme_row = next(r for r in data_rows if r[1] == "https://acme.com")
        assert acme_row[0] == "Acme"
        assert acme_row[2] == "existing2"

    def test_handles_commas_in_fields(self, tmp_path, monkeypatch):
        """Les virgules dans les champs quotes sont gerees correctement."""
        header = self._make_header()
        row = ["Acme", "https://acme.com"] + [f"v{i}" for i in range(2, 22)] + ["Strategie, angle"]
        self._setup_new_csv(tmp_path, [header, row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows[1]) == 23
        assert rows[1][22] == "Strategie, angle"


# ===========================================================================
# Tests post_process_csv - cas supplementaires
# ===========================================================================


class TestPostProcessCsvExtra:
    """Tests supplementaires pour couvrir les branches manquantes."""

    def _make_header(self) -> list[str]:
        return ["Societe", "Site Web"] + [f"col{i}" for i in range(2, 23)]

    def _make_row(self, name: str, url: str, prefix: str = "v") -> list[str]:
        return [name, url] + [f"{prefix}{i}" for i in range(2, 23)]

    def _final_csv_path(self, tmp_path) -> str:
        return str(tmp_path / "output" / "company_report.csv")

    def test_blank_lines_stripped(self, tmp_path, monkeypatch):
        """Les lignes vides dans le CSV brut sont ignorees."""
        header = self._make_header()
        row = self._make_row("Acme", "https://acme.com")
        # Contenu avec des lignes vides intercalees
        content = ",".join(header) + "\n\n" + ",".join(row) + "\n\n"

        csv_path = tmp_path / "output" / "company_report_new.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(content, encoding="utf-8")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows) == 2  # header + 1 data row

    def test_only_markdown_fences_warns(self, tmp_path, monkeypatch, capsys):
        """Un CSV contenant uniquement des code fences est vide apres nettoyage."""
        csv_path = tmp_path / "output" / "company_report_new.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text("```csv\n```\n", encoding="utf-8")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_header_only_warns(self, tmp_path, monkeypatch, capsys):
        """Un CSV avec uniquement le header et aucune donnee."""
        header = self._make_header()
        csv_path = tmp_path / "output" / "company_report_new.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(",".join(header) + "\n", encoding="utf-8")

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        # Ne crash pas, le CSV est cree avec juste le header
        rows = _read_csv(self._final_csv_path(tmp_path))
        assert len(rows) >= 1

    def test_existing_row_too_short_padded(self, tmp_path, monkeypatch):
        """Les lignes existantes avec moins de 23 colonnes sont completees lors de la validation."""
        header = self._make_header()
        short_existing = ["OldCo", "https://oldco.com"] + ["x"] * 10  # 12 cols
        new_row = self._make_row("NewCo", "https://newco.com")

        csv_path = str(tmp_path / "output" / "company_report.csv")
        _write_csv(csv_path, [header, short_existing], encoding="utf-8-sig")
        new_csv_path = str(tmp_path / "output" / "company_report_new.csv")
        _write_csv(new_csv_path, [header, new_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        for row in rows[1:]:
            assert len(row) == 23

    def test_existing_row_too_long_truncated(self, tmp_path, monkeypatch):
        """Les lignes existantes avec plus de 23 colonnes sont tronquees."""
        header = self._make_header()
        long_existing = ["OldCo", "https://oldco.com"] + ["x"] * 30  # 32 cols
        new_row = self._make_row("NewCo", "https://newco.com")

        csv_path = str(tmp_path / "output" / "company_report.csv")
        _write_csv(csv_path, [header, long_existing], encoding="utf-8-sig")
        new_csv_path = str(tmp_path / "output" / "company_report_new.csv")
        _write_csv(new_csv_path, [header, new_row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        post_process_csv(
            new_csv_path="output/company_report_new.csv",
            final_csv_path="output/company_report.csv",
        )

        rows = _read_csv(self._final_csv_path(tmp_path))
        for row in rows[1:]:
            assert len(row) == 23

    def test_oserror_on_temp_delete(self, tmp_path, monkeypatch, capsys):
        """Un OSError lors de la suppression du fichier temporaire affiche un warning."""
        header = self._make_header()
        row = self._make_row("Acme", "https://acme.com")
        new_csv_path = str(tmp_path / "output" / "company_report_new.csv")
        _write_csv(new_csv_path, [header, row])

        monkeypatch.setattr(csv_module, "__file__", _fake_file_path(tmp_path))
        with patch("os.remove", side_effect=OSError("permission denied")):
            post_process_csv(
                new_csv_path="output/company_report_new.csv",
                final_csv_path="output/company_report.csv",
            )

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "temporaire" in captured.out
