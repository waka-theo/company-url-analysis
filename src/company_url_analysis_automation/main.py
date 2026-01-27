#!/usr/bin/env python
import csv
import io
import json
import os
import shutil
import sys
from datetime import datetime

from company_url_analysis_automation.crew import CompanyUrlAnalysisAutomationCrew
from company_url_analysis_automation.search_crew import SearchCrew

# This main file is intended to be a way for your to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

CSV_FINAL_PATH = "output/company_report.csv"
CSV_NEW_PATH = "output/company_report_new.csv"
EXPECTED_COLUMNS = 23
URL_COLUMN_INDEX = 1  # Colonne "Site Web" (0-based)
SEARCH_CRITERIA_DEFAULT = "search_criteria.json"
SEARCH_RAW_OUTPUT = "output/search_results_raw.json"

SearchCriteria = dict[str, str | int | list[str]]


def load_urls(test_mode=True):
    """Load URLs from JSON file. Use test_mode=True for liste_test.json (5 URLs), False for liste.json (976 URLs)."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    filename = "liste_test.json" if test_mode else "liste.json"
    json_path = os.path.join(project_root, filename)
    with open(json_path) as f:
        return json.load(f)


def normalize_url(url: str) -> str:
    """Normalise une URL pour la deduplication (protocole, www, trailing slash, casse)."""
    url = url.strip().lower().rstrip("/")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix) :]
            break
    if url.startswith("www."):
        url = url[4:]
    return url


def load_existing_csv(
    csv_path: str,
) -> tuple[list[str] | None, dict[str, list[str]]]:
    """
    Charge le CSV existant et retourne (header, {url_normalisee: row}).
    Retourne (None, {}) si le fichier n'existe pas ou est vide.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(project_root, csv_path)

    if not os.path.exists(full_path):
        return None, {}

    with open(full_path, encoding="utf-8-sig") as f:
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
        if len(row) > URL_COLUMN_INDEX and row[URL_COLUMN_INDEX].strip():
            url_key = normalize_url(row[URL_COLUMN_INDEX])
            rows_dict[url_key] = row

    return header, rows_dict


def post_process_csv(
    new_csv_path: str = CSV_NEW_PATH,
    final_csv_path: str = CSV_FINAL_PATH,
    expected_columns: int = EXPECTED_COLUMNS,
) -> None:
    """
    Post-traitement incremental du CSV :
    - Lit le CSV existant (company_report.csv)
    - Lit le nouveau CSV genere par CrewAI (company_report_new.csv)
    - Merge par URL (colonne Site Web) : update si existe, append sinon
    - Backup automatique avant merge
    - Re-encode en UTF-8 BOM
    - Valide la structure (23 colonnes)
    - Supprime le fichier temporaire
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 1. Charger le CSV existant
    existing_header, existing_rows = load_existing_csv(final_csv_path)

    # 2. Charger le nouveau CSV
    new_full_path = os.path.join(project_root, new_csv_path)
    if not os.path.exists(new_full_path):
        print(f"[WARNING] Nouveau CSV non trouve : {new_full_path}")
        return

    with open(new_full_path, encoding="utf-8") as f:
        raw_content = f.read()

    if not raw_content.strip():
        print("[WARNING] Nouveau CSV vide, pas de post-processing")
        return

    # Nettoyage des artefacts markdown (code fences, lignes vides)
    cleaned_lines = []
    for line in raw_content.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if not stripped:
            continue
        cleaned_lines.append(line)
    raw_content = "\n".join(cleaned_lines)

    if not raw_content.strip():
        print("[WARNING] Nouveau CSV vide apres nettoyage markdown")
        return

    reader = csv.reader(io.StringIO(raw_content))
    new_rows = list(reader)

    if not new_rows:
        print("[WARNING] Nouveau CSV sans lignes")
        return

    # 3. Separer header et donnees du nouveau CSV
    new_header = new_rows[0]
    new_data_rows = new_rows[1:]

    # 4. Determiner le header final
    final_header = existing_header if existing_header else new_header

    # 5. Backup du fichier existant avant merge
    final_full_path = os.path.join(project_root, final_csv_path)
    if os.path.exists(final_full_path) and existing_rows:
        backup_dir = os.path.join(project_root, "output", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"company_report_{timestamp}.csv")
        shutil.copy2(final_full_path, backup_path)
        print(f"[INFO] Backup cree : {backup_path}")

    # 6. Merger les donnees
    merged_rows = dict(existing_rows)
    new_count = 0
    updated_count = 0

    for row in new_data_rows:
        # Validation colonnes
        if len(row) > expected_columns:
            row = row[:expected_columns]
        elif len(row) < expected_columns:
            row.extend(["Non trouvé"] * (expected_columns - len(row)))

        if len(row) > URL_COLUMN_INDEX and row[URL_COLUMN_INDEX].strip():
            url_key = normalize_url(row[URL_COLUMN_INDEX])
            if url_key in merged_rows:
                updated_count += 1
            else:
                new_count += 1
            merged_rows[url_key] = row

    # 7. Valider toutes les lignes (y compris les existantes)
    validated_rows: list[list[str]] = []
    for row in merged_rows.values():
        if len(row) > expected_columns:
            row = row[:expected_columns]
        elif len(row) < expected_columns:
            row.extend(["Non trouvé"] * (expected_columns - len(row)))
        validated_rows.append(row)

    # 8. Ecrire le fichier final
    os.makedirs(os.path.dirname(final_full_path), exist_ok=True)

    with open(final_full_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(final_header)
        writer.writerows(validated_rows)

    # 9. Supprimer le fichier temporaire
    try:
        os.remove(new_full_path)
    except OSError:
        print(f"[WARNING] Impossible de supprimer le fichier temporaire : {new_full_path}")

    total = len(validated_rows)
    print(
        f"[OK] CSV incremental : {total} entreprise(s) total "
        f"({new_count} nouvelle(s), {updated_count} mise(s) a jour), "
        f"{expected_columns} colonnes, encodage UTF-8 BOM"
    )


def run():
    """
    Run the crew.
    """
    urls = load_urls()
    inputs = {"urls": urls}
    CompanyUrlAnalysisAutomationCrew().crew().kickoff(inputs=inputs)
    post_process_csv()


def train():
    """
    Train the crew for a given number of iterations.
    """
    urls = load_urls()
    inputs = {"urls": urls}
    try:
        CompanyUrlAnalysisAutomationCrew().crew().train(
            n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}") from e


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        CompanyUrlAnalysisAutomationCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}") from e


def test():
    """
    Test the crew execution and returns the results.
    """
    urls = load_urls()
    inputs = {"urls": urls}
    try:
        CompanyUrlAnalysisAutomationCrew().crew().test(
            n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}") from e


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: main.py <command> [<args>]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "run":
        run()
    elif command == "train":
        train()
    elif command == "replay":
        replay()
    elif command == "test":
        test()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
