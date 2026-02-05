#!/usr/bin/env python
"""Point d'entree CLI pour WakaStart Leads."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from wakastart_leads.crews.analysis import AnalysisCrew
from wakastart_leads.crews.enrichment import EnrichmentCrew
from wakastart_leads.crews.search import SearchCrew
from wakastart_leads.shared.utils import (
    ANALYSIS_INPUT,
    ANALYSIS_OUTPUT,
    ENRICHMENT_INPUT,
    ENRICHMENT_OUTPUT,
    SEARCH_INPUT,
    SEARCH_OUTPUT,
    cleanup_old_logs,
    load_urls,
    merge_results_to_csv,
    normalize_url,
    post_process_csv,
    run_parallel,
)


def _setup_log_file(crew_output_dir: Path, workflow: str) -> str:
    """Cree le dossier de logs et retourne le chemin du fichier de log."""
    log_dir = crew_output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{workflow}_{timestamp}.json"
    return str(log_path)


def run() -> None:
    """Run the analysis crew."""
    parser = argparse.ArgumentParser(description="Run the analysis crew")
    parser.add_argument(
        "--parallel",
        "-p",
        type=int,
        default=1,
        help="Nombre de workers paralleles (1 = sequentiel)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Mode batch legacy (toutes URLs en un seul kickoff)",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=1,
        help="Nombre de retry par URL en cas d'echec",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout par URL en secondes (defaut: 600)",
    )

    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    urls = load_urls(ANALYSIS_INPUT)

    if args.batch:
        _run_batch_mode(urls)
    else:
        asyncio.run(_run_parallel_mode(urls, args))


def _run_batch_mode(urls: list[str]) -> None:
    """Mode batch legacy : toutes les URLs en un seul kickoff."""
    inputs = {"urls": urls}

    crew_instance = AnalysisCrew()
    crew_instance.log_file = _setup_log_file(ANALYSIS_OUTPUT, "run")
    print(f"[INFO] Mode batch - Logs: {crew_instance.log_file}")

    crew_instance.crew().kickoff(inputs=inputs)

    post_process_csv(
        new_csv_path=ANALYSIS_OUTPUT / "company_report_new.csv",
        final_csv_path=ANALYSIS_OUTPUT / "company_report.csv",
        backup_dir=ANALYSIS_OUTPUT / "backups",
    )

    cleanup_old_logs(ANALYSIS_OUTPUT / "logs")


async def _run_parallel_mode(urls: list[str], args: argparse.Namespace) -> None:
    """Mode parallele : chaque URL est traitee independamment."""
    log_dir = ANALYSIS_OUTPUT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Traitement de {len(urls)} URL(s) avec {args.parallel} worker(s)")
    print(f"[INFO] Timeout: {args.timeout}s par URL, Retry: {args.retry}")

    results = await run_parallel(
        urls=urls,
        crew_class=AnalysisCrew,
        log_dir=log_dir,
        max_workers=args.parallel,
        timeout=args.timeout,
        retry_count=args.retry,
    )

    # Fusion des resultats
    merge_results_to_csv(
        results=results,
        output_path=ANALYSIS_OUTPUT / "company_report.csv",
        backup_dir=ANALYSIS_OUTPUT / "backups",
    )

    # Resume
    success = sum(1 for r in results if r.status.value == "success")
    failed = sum(1 for r in results if r.status.value == "failed")
    timeout = sum(1 for r in results if r.status.value == "timeout")

    print(f"\n{'=' * 50}")
    print("[DONE] Resultats:")
    print(f"  - Succes: {success}")
    print(f"  - Echecs: {failed}")
    print(f"  - Timeouts: {timeout}")
    print(f"[OUTPUT] {ANALYSIS_OUTPUT / 'company_report.csv'}")

    cleanup_old_logs(log_dir)


def search() -> None:
    """Search for SaaS company URLs based on criteria."""
    parser = argparse.ArgumentParser(description="Search for SaaS company URLs")
    parser.add_argument("--criteria", type=str, help="Path to JSON criteria file")
    parser.add_argument("--output", type=str, help="Output file path")

    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    criteria_path = Path(args.criteria) if args.criteria else SEARCH_INPUT / "search_criteria.json"

    with open(criteria_path, encoding="utf-8") as f:
        criteria = json.load(f)

    search_criteria_text = _format_search_criteria(criteria)
    max_results = criteria.get("max_results", 50)

    inputs = {
        "search_criteria": search_criteria_text,
        "max_results": int(max_results) if max_results else 50,
        "sector": str(criteria.get("sector", "technologie")),
    }

    print("[INFO] Lancement recherche avec criteres:")
    print(search_criteria_text)

    search_crew = SearchCrew()
    search_crew.log_file = _setup_log_file(SEARCH_OUTPUT, "search")
    print(f"[INFO] Logs: {search_crew.log_file}")

    search_crew.crew().kickoff(inputs=inputs)

    _post_process_search_results(args.output)
    cleanup_old_logs(SEARCH_OUTPUT / "logs")


def enrich() -> None:
    """Enrich company CSV with WakaStart analysis."""
    import csv
    import io

    parser = argparse.ArgumentParser(description="Enrich company CSV")
    parser.add_argument("--input", "-i", type=str, default="Datas entreprises Tom - Affinage n°6.csv")
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--batch-size", "-b", type=int, default=20)
    parser.add_argument("--test", action="store_true")

    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    input_path = Path(args.input)
    if not input_path.is_absolute():
        if (ENRICHMENT_INPUT / args.input).exists():
            input_path = ENRICHMENT_INPUT / args.input
        else:
            input_path = Path.cwd() / args.input

    print(f"[INFO] Chargement du CSV: {input_path}")

    with open(input_path, encoding="utf-8-sig") as f:
        raw_content = f.read()

    reader = csv.DictReader(io.StringIO(raw_content))
    header = list(reader.fieldnames or [])
    rows = list(reader)

    print(f"[INFO] {len(rows)} ligne(s) chargee(s)")

    all_urls = _extract_urls_from_csv(rows)

    if args.test:
        all_urls = all_urls[:20]
        print(f"[INFO] Mode test: {len(all_urls)} URL(s)")

    if not all_urls:
        print("[WARNING] Aucune URL a traiter")
        return

    accumulated_file = ENRICHMENT_OUTPUT / "enrichment_accumulated.json"
    all_enrichments, processed_urls = _load_accumulated_results(accumulated_file)

    urls_to_process = [url for url in all_urls if normalize_url(url) not in processed_urls]
    print(f"[INFO] {len(urls_to_process)} URL(s) restante(s)")

    if urls_to_process:
        batch_size = args.batch_size
        for i in range(0, len(urls_to_process), batch_size):
            batch = urls_to_process[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(urls_to_process) + batch_size - 1) // batch_size

            print(f"\n[INFO] === Batch {batch_num}/{total_batches} ===")

            urls_text = "\n".join(f"- {url}" for url in batch)
            inputs = {"urls": urls_text}

            enrichment_crew = EnrichmentCrew()
            enrichment_crew.log_file = _setup_log_file(ENRICHMENT_OUTPUT, "enrich")

            crew_output = enrichment_crew.crew().kickoff(inputs=inputs)
            batch_results = _parse_enrichment_output(crew_output.raw)

            all_enrichments.extend(batch_results)

            with open(accumulated_file, "w", encoding="utf-8") as f:
                json.dump(all_enrichments, f, ensure_ascii=False, indent=2)

    rows = _update_csv_with_enrichment(rows, all_enrichments)

    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = ENRICHMENT_OUTPUT / f"{input_path.stem}_enriched_{timestamp}.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[OK] Fichier: {output_path}")

    cleanup_old_logs(ENRICHMENT_OUTPUT / "logs")


def _format_search_criteria(criteria: dict) -> str:
    """Formate les criteres de recherche en texte lisible."""
    parts: list[str] = []
    if criteria.get("keywords"):
        kw = criteria["keywords"]
        parts.append(f"Mots-cles: {', '.join(kw) if isinstance(kw, list) else kw}")
    if criteria.get("sector"):
        parts.append(f"Secteur: {criteria['sector']}")
    if criteria.get("geographic_zone"):
        parts.append(f"Zone: {criteria['geographic_zone']}")
    if criteria.get("company_size"):
        parts.append(f"Taille: {criteria['company_size']}")
    if criteria.get("creation_year_min"):
        parts.append(f"Annee min: {criteria['creation_year_min']}")
    return "\n".join(parts) if parts else "Recherche large SaaS France"


def _post_process_search_results(output_path: str | None) -> list[str]:
    """Post-traitement des resultats de recherche."""
    raw_path = SEARCH_OUTPUT / "search_results_raw.json"
    if not raw_path.exists():
        return []

    with open(raw_path, encoding="utf-8") as f:
        content = f.read().strip()

    if content.startswith("```"):
        lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        urls = json.loads(content)
    except json.JSONDecodeError:
        return []

    seen: set[str] = set()
    final_urls: list[str] = []
    for url in urls:
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        normalized = normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            final_urls.append(url)

    if output_path:
        final_path = Path(output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = SEARCH_OUTPUT / f"search_urls_{timestamp}.json"

    final_path.parent.mkdir(parents=True, exist_ok=True)
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(final_urls, f, indent=2, ensure_ascii=False)

    raw_path.unlink(missing_ok=True)
    print(f"[OK] {len(final_urls)} URL(s) -> {final_path}")
    return final_urls


def _extract_urls_from_csv(rows: list[dict]) -> list[str]:
    """Extrait les URLs de la colonne Site Internet."""
    urls: list[str] = []
    for row in rows:
        url = row.get("Site Internet", "").strip()
        if not url or (" " in url and not url.startswith("http")):
            continue
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        urls.append(url)
    return urls


def _load_accumulated_results(path: Path) -> tuple[list[dict], set[str]]:
    """Charge les resultats accumules existants."""
    if not path.exists():
        return [], set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        processed = {normalize_url(e.get("url", "")) for e in data if e.get("url")}
        return data, processed
    except (json.JSONDecodeError, OSError):
        return [], set()


def _parse_enrichment_output(raw: str) -> list[dict]:
    """Parse le resultat JSON d'enrichissement."""
    if not raw:
        return []
    content = raw.strip()
    lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
    content = "\n".join(lines).strip()
    if not content.startswith("["):
        match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
        if match:
            content = match.group(0)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return []


def _update_csv_with_enrichment(rows: list[dict], enrichments: list[dict]) -> list[dict]:
    """Met a jour les lignes du CSV avec les donnees d'enrichissement."""
    index = {normalize_url(e.get("url", "")): e for e in enrichments if e.get("url")}
    for row in rows:
        url = row.get("Site Internet", "").strip()
        if not url:
            continue
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        normalized = normalize_url(url)
        if normalized in index:
            e = index[normalized]
            row["Nationalite"] = e.get("nationalite", "")
            row["Solution Saas"] = e.get("solution_saas", "")
            row["Pertinance"] = e.get("pertinence", "")
            row["Explication"] = e.get("explication", "")
    return rows


def train() -> None:
    """Train the crew."""
    urls = load_urls(ANALYSIS_INPUT)
    AnalysisCrew().crew().train(n_iterations=int(sys.argv[2]), filename=sys.argv[3], inputs={"urls": urls})


def replay() -> None:
    """Replay from a specific task."""
    AnalysisCrew().crew().replay(task_id=sys.argv[2])


def test() -> None:
    """Test the crew."""
    urls = load_urls(ANALYSIS_INPUT)
    AnalysisCrew().crew().test(n_iterations=int(sys.argv[2]), openai_model_name=sys.argv[3], inputs={"urls": urls})


def cli() -> None:
    """Point d'entree CLI principal."""
    if len(sys.argv) < 2:
        print("Usage: python -m wakastart_leads.main <command>")
        print("Commands: run, search, enrich, train, replay, test")
        sys.exit(1)

    command = sys.argv[1]
    commands = {
        "run": run,
        "search": search,
        "enrich": enrich,
        "train": train,
        "replay": replay,
        "test": test,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
