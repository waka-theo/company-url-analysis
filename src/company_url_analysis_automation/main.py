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


LOG_DIR = "output/logs"


def _setup_log_file(workflow: str) -> str:
    """
    Cree le dossier de logs et retourne le chemin du fichier de log.
    workflow: 'run' ou 'search' -> output/logs/run/ ou output/logs/search/
    """
    project_root = _get_project_root()
    log_dir = os.path.join(project_root, LOG_DIR, workflow)
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{workflow}_{timestamp}.json")
    return log_path


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


def _get_project_root() -> str:
    """Retourne le chemin absolu de la racine du projet."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_search_criteria(criteria_path: str | None = None) -> SearchCriteria:
    """
    Charge les criteres de recherche depuis un fichier JSON.
    Si aucun fichier n'est specifie, utilise search_criteria.json a la racine du projet.
    """
    project_root = _get_project_root()

    if criteria_path:
        json_path = criteria_path if os.path.isabs(criteria_path) else os.path.join(project_root, criteria_path)
    else:
        json_path = os.path.join(project_root, SEARCH_CRITERIA_DEFAULT)

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Fichier de criteres non trouve: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        criteria: SearchCriteria = json.load(f)

    return criteria


def format_search_criteria(criteria: SearchCriteria) -> str:
    """
    Formate les criteres de recherche en texte lisible pour l'agent.
    Chaque critere fourni est converti en ligne descriptive.
    """
    parts: list[str] = []

    if criteria.get("keywords"):
        keywords = criteria["keywords"]
        if isinstance(keywords, list):
            parts.append(f"Mots-cles: {', '.join(str(k) for k in keywords)}")
        else:
            parts.append(f"Mots-cles: {keywords}")

    if criteria.get("sector"):
        parts.append(f"Secteur: {criteria['sector']}")

    if criteria.get("geographic_zone"):
        parts.append(f"Zone geographique: {criteria['geographic_zone']}")

    if criteria.get("company_size"):
        parts.append(f"Taille entreprise: {criteria['company_size']}")

    if criteria.get("creation_year_min"):
        parts.append(f"Annee creation min: {criteria['creation_year_min']}")

    if criteria.get("creation_year_max"):
        parts.append(f"Annee creation max: {criteria['creation_year_max']}")

    if criteria.get("naf_codes"):
        codes = criteria["naf_codes"]
        if isinstance(codes, list):
            parts.append(f"Codes NAF: {', '.join(str(c) for c in codes)}")

    if criteria.get("exclude_domains"):
        domains = criteria["exclude_domains"]
        if isinstance(domains, list):
            parts.append(f"Domaines exclus: {', '.join(str(d) for d in domains)}")

    return "\n".join(parts) if parts else "Aucun critere specifique - recherche large de startups/scale-ups SaaS en France"


def post_process_search_results(
    raw_output_path: str = SEARCH_RAW_OUTPUT,
    final_output_path: str | None = None,
) -> list[str]:
    """
    Post-traitement des resultats de recherche :
    1. Parse le JSON brut (nettoyage markdown si necessaire)
    2. Normalise les URLs (protocole https, deduplication)
    3. Ecrit le fichier final JSON (Array<string>)
    4. Supprime le fichier brut temporaire
    """
    project_root = _get_project_root()
    raw_path = os.path.join(project_root, raw_output_path)

    if not os.path.exists(raw_path):
        print(f"[WARNING] Fichier brut non trouve: {raw_path}")
        return []

    with open(raw_path, encoding="utf-8") as f:
        raw_content = f.read().strip()

    if not raw_content:
        print("[WARNING] Fichier brut vide")
        return []

    # Nettoyage markdown (code fences)
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw_content = "\n".join(lines).strip()

    if not raw_content:
        print("[WARNING] Fichier brut vide apres nettoyage markdown")
        return []

    # Parse JSON
    try:
        urls_raw: list[str] = json.loads(raw_content)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON invalide dans le fichier brut: {e}")
        return []

    if not isinstance(urls_raw, list):
        print("[ERROR] Le fichier brut ne contient pas un JSON array")
        return []

    # Normalisation et deduplication
    seen: set[str] = set()
    urls_final: list[str] = []

    for url in urls_raw:
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url:
            continue

        # Assurer le protocole https
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Normaliser pour deduplication
        normalized = normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            urls_final.append(url)

    # Determiner le fichier de sortie
    if final_output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output_path = f"output/search_urls_{timestamp}.json"

    final_path = (
        final_output_path if os.path.isabs(final_output_path) else os.path.join(project_root, final_output_path)
    )
    os.makedirs(os.path.dirname(final_path), exist_ok=True)

    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(urls_final, f, indent=2, ensure_ascii=False)

    # Supprimer le fichier brut
    try:
        os.remove(raw_path)
    except OSError:
        pass

    print(f"[OK] Recherche terminee: {len(urls_final)} URL(s) trouvee(s)")
    print(f"[OK] Fichier: {final_path}")

    return urls_final


def search():
    """
    Search for SaaS company URLs based on criteria.
    Usage:
      python main.py search
      python main.py search --criteria path/to/file.json
      python main.py search --output output/mes_urls.json
    """
    import argparse

    parser = argparse.ArgumentParser(description="Search for SaaS company URLs")
    parser.add_argument("--criteria", type=str, help="Path to JSON criteria file (default: search_criteria.json)")
    parser.add_argument("--output", type=str, help="Output file path (default: output/search_urls_TIMESTAMP.json)")

    # Filtrer les arguments (sys.argv[0] est le script, sys.argv[1] est "search")
    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    # Charger les criteres
    criteria = load_search_criteria(args.criteria)

    # Formater pour l'agent
    search_criteria_text = format_search_criteria(criteria)
    max_results = criteria.get("max_results", 50)

    inputs: dict[str, str | int] = {
        "search_criteria": search_criteria_text,
        "max_results": int(max_results) if max_results else 50,
        "sector": str(criteria.get("sector", "technologie")),
    }

    print("[INFO] Lancement recherche avec criteres:")
    print(search_criteria_text)
    print(f"[INFO] Maximum resultats: {max_results}")

    search_crew = SearchCrew()
    search_crew.log_file = _setup_log_file("search")
    print(f"[INFO] Logs: {search_crew.log_file}")

    search_crew.crew().kickoff(inputs=inputs)

    post_process_search_results(final_output_path=args.output)


def run():
    """
    Run the crew.
    """
    urls = load_urls()
    inputs = {"urls": urls}

    crew_instance = CompanyUrlAnalysisAutomationCrew()
    crew_instance.log_file = _setup_log_file("run")
    print(f"[INFO] Logs: {crew_instance.log_file}")

    crew_instance.crew().kickoff(inputs=inputs)
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
    elif command == "search":
        search()
    elif command == "train":
        train()
    elif command == "replay":
        replay()
    elif command == "test":
        test()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: run, search, train, replay, test")
        sys.exit(1)
