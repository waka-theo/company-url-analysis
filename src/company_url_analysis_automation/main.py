#!/usr/bin/env python
import csv
import io
import json
import os
import shutil
import sys
from datetime import datetime

from company_url_analysis_automation.crew import CompanyUrlAnalysisAutomationCrew
from company_url_analysis_automation.enrichment_crew import EnrichmentCrew
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
ENRICHMENT_RAW_OUTPUT = "output/enrichment_results.json"

SearchCriteria = dict[str, str | int | list[str]]
EnrichmentResult = dict[str, str]


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


def load_enrichment_csv(filepath: str) -> tuple[list[str], list[dict[str, str]]]:
    """
    Charge le CSV d'enrichissement et retourne (header, rows).
    Chaque row est un dict avec les noms de colonnes comme cles.
    """
    project_root = _get_project_root()
    full_path = filepath if os.path.isabs(filepath) else os.path.join(project_root, filepath)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Fichier CSV non trouve: {full_path}")

    with open(full_path, encoding="utf-8-sig") as f:
        raw_content = f.read()

    if not raw_content.strip():
        raise ValueError("Fichier CSV vide")

    reader = csv.DictReader(io.StringIO(raw_content))
    header = reader.fieldnames or []
    rows = list(reader)

    return list(header), rows


def extract_urls_from_enrichment_csv(rows: list[dict[str, str]]) -> list[str]:
    """
    Extrait les URLs de la colonne 'Site Internet' du CSV.
    Normalise les URLs (ajoute https:// si absent, nettoie les espaces).
    """
    urls: list[str] = []

    for row in rows:
        url = row.get("Site Internet", "").strip()
        if not url:
            continue

        # Ignorer les entrees qui ne sont pas des URLs (ex: "Education Lily Media")
        if " " in url and not url.startswith("http"):
            continue

        # Normaliser : ajouter https:// si absent
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        urls.append(url)

    return urls


def parse_enrichment_output(raw_output: str) -> list[EnrichmentResult]:
    """
    Parse le resultat JSON d'enrichissement depuis une chaine.
    Nettoie les artefacts markdown si presents.
    """
    if not raw_output:
        print("[WARNING] Output vide")
        return []

    raw_content = raw_output.strip()

    # Nettoyage markdown (code fences) - ligne par ligne
    lines = raw_content.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Ignorer les lignes de code fence (```json, ```, etc.)
        if stripped.startswith("```"):
            continue
        cleaned_lines.append(line)
    raw_content = "\n".join(cleaned_lines).strip()

    # Essayer d'extraire le JSON array avec regex si necessaire
    if not raw_content.startswith("["):
        import re
        # Chercher un JSON array dans le contenu
        match = re.search(r'\[\s*\{.*\}\s*\]', raw_content, re.DOTALL)
        if match:
            raw_content = match.group(0)

    if not raw_content:
        print("[WARNING] Output vide apres nettoyage markdown")
        return []

    # Parse JSON
    try:
        results: list[EnrichmentResult] = json.loads(raw_content)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON invalide dans l'output: {e}")
        print(f"[DEBUG] Contenu (500 premiers chars): {raw_content[:500]}")
        return []

    if not isinstance(results, list):
        print("[ERROR] L'output n'est pas un JSON array")
        return []

    print(f"[DEBUG] {len(results)} resultat(s) parses avec succes")
    return results


def parse_enrichment_results(raw_output_path: str) -> list[EnrichmentResult]:
    """
    Parse le fichier JSON de resultats d'enrichissement.
    Nettoie les artefacts markdown si presents.
    """
    project_root = _get_project_root()
    raw_path = os.path.join(project_root, raw_output_path)

    if not os.path.exists(raw_path):
        print(f"[WARNING] Fichier resultats non trouve: {raw_path}")
        return []

    with open(raw_path, encoding="utf-8") as f:
        raw_content = f.read().strip()

    if not raw_content:
        print("[WARNING] Fichier resultats vide")
        return []

    # Nettoyage markdown (code fences) - plus robuste
    # Supprimer les lignes qui contiennent uniquement des code fences
    lines = raw_content.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Ignorer les lignes de code fence (```json, ```, etc.)
        if stripped.startswith("```"):
            continue
        cleaned_lines.append(line)
    raw_content = "\n".join(cleaned_lines).strip()

    # Essayer d'extraire le JSON array avec regex si necessaire
    if not raw_content.startswith("["):
        import re
        # Chercher un JSON array dans le contenu
        match = re.search(r'\[\s*\{.*?\}\s*\]', raw_content, re.DOTALL)
        if match:
            raw_content = match.group(0)

    if not raw_content:
        print("[WARNING] Fichier resultats vide apres nettoyage markdown")
        return []

    # Parse JSON
    try:
        results: list[EnrichmentResult] = json.loads(raw_content)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON invalide dans les resultats: {e}")
        print(f"[DEBUG] Contenu (500 premiers chars): {raw_content[:500]}")
        return []

    if not isinstance(results, list):
        print("[ERROR] Les resultats ne sont pas un JSON array")
        return []

    print(f"[DEBUG] {len(results)} resultat(s) parses avec succes")
    return results


def update_csv_with_enrichment(
    rows: list[dict[str, str]],
    enrichments: list[EnrichmentResult],
) -> list[dict[str, str]]:
    """
    Met a jour les lignes du CSV avec les donnees d'enrichissement.
    Match par URL normalisee.
    """
    # Creer un index des enrichissements par URL normalisee
    enrichment_index: dict[str, EnrichmentResult] = {}
    for enrichment in enrichments:
        url = enrichment.get("url", "")
        if url:
            normalized = normalize_url(url)
            enrichment_index[normalized] = enrichment

    # Mettre a jour chaque ligne
    updated_count = 0
    for row in rows:
        url = row.get("Site Internet", "").strip()
        if not url:
            continue

        # Normaliser l'URL pour le match
        if not url.startswith(("http://", "https://")):
            url_for_match = f"https://{url}"
        else:
            url_for_match = url

        normalized = normalize_url(url_for_match)

        if normalized in enrichment_index:
            enrichment = enrichment_index[normalized]
            row["Nationalité"] = enrichment.get("nationalite", "")
            row["Solution Saas"] = enrichment.get("solution_saas", "")
            row["Pertinance"] = enrichment.get("pertinence", "")
            row["Explication"] = enrichment.get("explication", "")
            updated_count += 1

    print(f"[INFO] {updated_count} ligne(s) enrichie(s)")
    return rows


def save_enriched_csv(
    header: list[str],
    rows: list[dict[str, str]],
    output_path: str,
) -> None:
    """
    Sauvegarde le CSV enrichi avec encodage UTF-8 BOM pour Excel.
    """
    project_root = _get_project_root()
    full_path = output_path if os.path.isabs(output_path) else os.path.join(project_root, output_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] CSV enrichi sauvegarde: {full_path}")


def enrich():
    """
    Enrich company CSV with nationality, SaaS solution, relevance score and explanation.
    Usage:
      python main.py enrich
      python main.py enrich --test
      python main.py enrich --input path/to/file.csv --output path/to/output.csv
      python main.py enrich --batch-size 10
    """
    import argparse

    parser = argparse.ArgumentParser(description="Enrich company CSV with WakaStart analysis")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="Datas entreprises Tom - Affinage n°6.csv",
        help="Input CSV file path",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output CSV file path (default: input file with _enriched suffix)",
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=20,
        help="Number of URLs to process per batch (default: 20)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: process only first 20 URLs",
    )

    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    # 1. Charger le CSV d'entree
    print(f"[INFO] Chargement du CSV: {args.input}")
    try:
        header, rows = load_enrichment_csv(args.input)
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[INFO] {len(rows)} ligne(s) chargee(s)")

    # 2. Extraire les URLs
    all_urls = extract_urls_from_enrichment_csv(rows)
    print(f"[INFO] {len(all_urls)} URL(s) a traiter")

    # 3. Mode test : limiter a 20 URLs
    if args.test:
        all_urls = all_urls[:20]
        print(f"[INFO] Mode test: traitement de {len(all_urls)} URL(s)")

    if not all_urls:
        print("[WARNING] Aucune URL a traiter")
        sys.exit(0)

    # 4. Charger les resultats accumules existants (pour reprise)
    project_root = _get_project_root()
    accumulated_file = os.path.join(project_root, "output", "enrichment_accumulated.json")
    all_enrichments: list[EnrichmentResult] = []
    processed_urls: set[str] = set()

    if os.path.exists(accumulated_file):
        try:
            with open(accumulated_file, encoding="utf-8") as f:
                all_enrichments = json.load(f)
            # Extraire les URLs deja traitees
            for enrichment in all_enrichments:
                url = enrichment.get("url", "")
                if url:
                    processed_urls.add(normalize_url(url))
            print(f"[INFO] {len(all_enrichments)} resultat(s) existant(s) charges")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARNING] Impossible de charger les resultats existants: {e}")
            all_enrichments = []

    # Filtrer les URLs deja traitees
    urls_to_process = [
        url for url in all_urls
        if normalize_url(url) not in processed_urls
    ]
    print(f"[INFO] {len(urls_to_process)} URL(s) restante(s) a traiter")

    if not urls_to_process:
        print("[INFO] Toutes les URLs ont deja ete traitees")
    else:
        # 5. Traiter par batches
        batch_size = args.batch_size
        total_batches = (len(urls_to_process) + batch_size - 1) // batch_size

        for i in range(0, len(urls_to_process), batch_size):
            batch = urls_to_process[i : i + batch_size]
            batch_num = i // batch_size + 1

            print(f"\n[INFO] === Batch {batch_num}/{total_batches} ({len(batch)} URL(s)) ===")

            # Formater les URLs pour l'agent
            urls_text = "\n".join(f"- {url}" for url in batch)
            inputs = {"urls": urls_text}

            # Executer le crew
            enrichment_crew = EnrichmentCrew()
            enrichment_crew.log_file = _setup_log_file("enrich")
            print(f"[INFO] Logs: {enrichment_crew.log_file}")

            crew_output = enrichment_crew.crew().kickoff(inputs=inputs)

            # Parser les resultats de ce batch (directement depuis l'output du crew)
            batch_results = parse_enrichment_output(crew_output.raw)
            print(f"[INFO] Batch {batch_num}: {len(batch_results)} resultat(s)")

            # Accumuler les resultats
            all_enrichments.extend(batch_results)

            # Sauvegarder les resultats accumules (pour reprise en cas d'interruption)
            with open(accumulated_file, "w", encoding="utf-8") as f:
                json.dump(all_enrichments, f, ensure_ascii=False, indent=2)
            print(f"[INFO] Resultats sauvegardes: {len(all_enrichments)} total")

    print(f"\n[INFO] Total enrichissements: {len(all_enrichments)}")

    # 6. Mettre a jour le CSV
    rows = update_csv_with_enrichment(rows, all_enrichments)

    # 7. Sauvegarder le CSV enrichi
    if args.output:
        output_path = args.output
    else:
        # Generer un nom de fichier avec suffix _enriched
        base, ext = os.path.splitext(args.input)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/{os.path.basename(base)}_enriched_{timestamp}{ext}"

    save_enriched_csv(header, rows, output_path)

    print(f"\n[OK] Enrichissement termine!")
    print(f"[OK] Fichier: {output_path}")
    print(f"[OK] Resultats JSON: {accumulated_file}")


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
    elif command == "enrich":
        enrich()
    elif command == "train":
        train()
    elif command == "replay":
        replay()
    elif command == "test":
        test()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: run, search, enrich, train, replay, test")
        sys.exit(1)
