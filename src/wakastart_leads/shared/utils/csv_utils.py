"""Utilitaires pour la manipulation de fichiers CSV."""

import csv
import io
import shutil
from datetime import datetime
from pathlib import Path

from .url_utils import normalize_url


def load_existing_csv(
    csv_path: Path,
    url_column_index: int = 1,
) -> tuple[list[str] | None, dict[str, list[str]]]:
    """
    Charge le CSV existant et retourne (header, {url_normalisee: row}).
    Retourne (None, {}) si le fichier n'existe pas ou est vide.
    """
    if not csv_path.exists():
        return None, {}

    with open(csv_path, encoding="utf-8-sig") as f:
        raw_content = f.read()

    if not raw_content.strip():
        return None, {}

    reader = csv.reader(io.StringIO(raw_content))
    rows = list(reader)

    if not rows:
        return None, {}

    header = rows[0]
    rows_dict: dict[str, list[str]] = {}
    for row in rows[1:]:
        if len(row) > url_column_index and row[url_column_index].strip():
            url_key = normalize_url(row[url_column_index])
            rows_dict[url_key] = row

    return header, rows_dict


def clean_markdown_artifacts(content: str) -> str:
    """Nettoie les artefacts markdown (code fences, lignes vides)."""
    cleaned_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if not stripped:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def post_process_csv(
    new_csv_path: Path,
    final_csv_path: Path,
    backup_dir: Path,
    expected_columns: int = 23,
    url_column_index: int = 1,
) -> None:
    """
    Post-traitement incremental du CSV.
    """
    # 1. Charger le CSV existant
    existing_header, existing_rows = load_existing_csv(final_csv_path, url_column_index)

    # 2. Charger le nouveau CSV
    if not new_csv_path.exists():
        print(f"[WARNING] Nouveau CSV non trouve : {new_csv_path}")
        return

    with open(new_csv_path, encoding="utf-8") as f:
        raw_content = f.read()

    if not raw_content.strip():
        print("[WARNING] Nouveau CSV vide, pas de post-processing")
        return

    # Nettoyage markdown
    raw_content = clean_markdown_artifacts(raw_content)

    if not raw_content.strip():
        print("[WARNING] Nouveau CSV vide apres nettoyage markdown")
        return

    reader = csv.reader(io.StringIO(raw_content))
    new_rows = list(reader)

    if not new_rows:
        print("[WARNING] Nouveau CSV sans lignes")
        return

    # 3. Separer header et donnees
    new_header = new_rows[0]
    new_data_rows = new_rows[1:]

    # 4. Determiner le header final
    final_header = existing_header if existing_header else new_header

    # 5. Backup avant merge
    if final_csv_path.exists() and existing_rows:
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"company_report_{timestamp}.csv"
        shutil.copy2(final_csv_path, backup_path)
        print(f"[INFO] Backup cree : {backup_path}")

    # 6. Merger les donnees
    merged_rows = dict(existing_rows)
    new_count = 0
    updated_count = 0

    for row in new_data_rows:
        if len(row) > expected_columns:
            row = row[:expected_columns]
        elif len(row) < expected_columns:
            row.extend(["Non trouve"] * (expected_columns - len(row)))

        if len(row) > url_column_index and row[url_column_index].strip():
            url_key = normalize_url(row[url_column_index])
            if url_key in merged_rows:
                updated_count += 1
            else:
                new_count += 1
            merged_rows[url_key] = row

    # 7. Valider toutes les lignes
    validated_rows: list[list[str]] = []
    for row in merged_rows.values():
        if len(row) > expected_columns:
            row = row[:expected_columns]
        elif len(row) < expected_columns:
            row.extend(["Non trouve"] * (expected_columns - len(row)))
        validated_rows.append(row)

    # 8. Ecrire le fichier final
    final_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(final_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(final_header)
        writer.writerows(validated_rows)

    # 9. Supprimer le fichier temporaire
    try:
        new_csv_path.unlink()
    except OSError:
        print(f"[WARNING] Impossible de supprimer le fichier temporaire : {new_csv_path}")

    total = len(validated_rows)
    print(
        f"[OK] CSV incremental : {total} entreprise(s) total "
        f"({new_count} nouvelle(s), {updated_count} mise(s) a jour), "
        f"{expected_columns} colonnes, encodage UTF-8 BOM"
    )
