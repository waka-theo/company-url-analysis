"""Module d'orchestration parallèle pour le traitement des URLs."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class RunStatus(Enum):
    """Statut d'exécution d'une URL."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class UrlResult:
    """Résultat du traitement d'une URL."""

    url: str
    status: RunStatus
    csv_row: str | None
    error: str | None
    duration_seconds: float


async def run_single_url(
    url: str,
    crew_class: Any,
    log_dir: Path,
    timeout: int = 600,
) -> UrlResult:
    """
    Exécute le crew pour une seule URL.

    Args:
        url: URL à traiter
        crew_class: Classe du crew à instancier
        log_dir: Dossier pour les logs
        timeout: Timeout en secondes

    Returns:
        UrlResult avec le statut et les données
    """
    start = datetime.now()
    domain = url.replace("https://", "").replace("http://", "").split("/")[0].replace("www.", "")

    try:
        crew_instance = crew_class()

        # Configurer log individuel
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir.mkdir(parents=True, exist_ok=True)
        crew_instance.log_file = str(log_dir / f"{domain}_{timestamp}.json")

        # Exécuter avec timeout
        result = await asyncio.wait_for(
            asyncio.to_thread(
                crew_instance.crew().kickoff,
                inputs={"url": url},
            ),
            timeout=timeout,
        )

        duration = (datetime.now() - start).total_seconds()
        return UrlResult(
            url=url,
            status=RunStatus.SUCCESS,
            csv_row=result.raw if hasattr(result, "raw") else str(result),
            error=None,
            duration_seconds=duration,
        )

    except asyncio.TimeoutError:
        return UrlResult(
            url=url,
            status=RunStatus.TIMEOUT,
            csv_row=None,
            error=f"Timeout après {timeout}s",
            duration_seconds=float(timeout),
        )
    except Exception as e:
        duration = (datetime.now() - start).total_seconds()
        return UrlResult(
            url=url,
            status=RunStatus.FAILED,
            csv_row=None,
            error=str(e),
            duration_seconds=duration,
        )


async def run_parallel(
    urls: list[str],
    crew_class: Any,
    log_dir: Path,
    max_workers: int = 3,
    timeout: int = 600,
    retry_count: int = 1,
    output_path: Path | None = None,
    on_result: Any = None,
) -> list[UrlResult]:
    """
    Execute le crew pour plusieurs URLs en parallele.

    Args:
        urls: Liste des URLs a traiter
        crew_class: Classe du crew a instancier
        log_dir: Dossier pour les logs
        max_workers: Nombre maximum d'executions simultanees
        timeout: Timeout par URL en secondes
        retry_count: Nombre de retry en cas d'echec
        output_path: Chemin du CSV pour sauvegarde incrementale (optionnel).
            Si fourni, chaque resultat est ecrit au CSV des qu'il est disponible.
        on_result: Callback optionnel appele avec chaque UrlResult des qu'il est pret.

    Returns:
        Liste de UrlResult pour chaque URL
    """
    semaphore = asyncio.Semaphore(max_workers)
    csv_lock = asyncio.Lock()

    async def run_with_retry(url: str) -> UrlResult:
        async with semaphore:
            last_result = None
            for attempt in range(retry_count + 1):
                result = await run_single_url(url, crew_class, log_dir, timeout)
                if result.status == RunStatus.SUCCESS:
                    break
                last_result = result
                if attempt < retry_count:
                    await asyncio.sleep(2**attempt)  # Backoff exponentiel
            else:
                result = last_result

            # Sauvegarde incrementale au CSV
            if output_path is not None:
                async with csv_lock:
                    append_result_to_csv(result, output_path)

            # Callback de notification
            if on_result is not None:
                on_result(result)

            return result

    tasks = [run_with_retry(url) for url in urls]
    return await asyncio.gather(*tasks)


CSV_HEADER = (
    "Societe,Site Web,Nationalite,Annee Creation,Solution SaaS,Pertinence (%),"
    "Strategie & Angle,Decideur 1 - Nom,Decideur 1 - Titre,Decideur 1 - Email,"
    "Decideur 1 - Telephone,Decideur 1 - LinkedIn,Decideur 2 - Nom,Decideur 2 - Titre,"
    "Decideur 2 - Email,Decideur 2 - Telephone,Decideur 2 - LinkedIn,Decideur 3 - Nom,"
    "Decideur 3 - Titre,Decideur 3 - Email,Decideur 3 - Telephone,Decideur 3 - LinkedIn,"
    "Page Gamma"
)

# Patterns d'en-tête à supprimer (avec/sans accents, variations)
HEADER_PATTERNS = [
    "Societe,Site Web,",
    "Société,Site Web,",
    "societe,site web,",
    "société,site web,",
]


def clean_csv_row(raw_row: str) -> str | None:
    """
    Nettoie une ligne CSV brute retournée par l'agent LLM.

    Supprime :
    - Les artefacts markdown (```, ```csv, etc.)
    - Les lignes d'en-tête répétées
    - Les espaces superflus

    Args:
        raw_row: Ligne brute retournée par l'agent

    Returns:
        Ligne nettoyée ou None si la ligne est vide/invalide
    """
    if not raw_row:
        return None

    # Supprimer les retours à la ligne et retours chariot
    line = raw_row.strip().replace("\n", " ").replace("\r", "")

    # Supprimer les artefacts markdown au début
    for prefix in ["```csv", "``` csv", "```CSV", "```"]:
        if line.startswith(prefix):
            line = line[len(prefix):].strip()

    # Supprimer les artefacts markdown à la fin
    if line.endswith("```"):
        line = line[:-3].strip()

    # Si la ligne contient un header suivi de données, extraire les données
    for pattern in HEADER_PATTERNS:
        # Chercher le pattern (case-insensitive)
        lower_line = line.lower()
        lower_pattern = pattern.lower()

        # Trouver toutes les occurrences du pattern
        idx = lower_line.find(lower_pattern)
        if idx != -1:
            # Si le header est au début, chercher où commencent les vraies données
            # Les données commencent après "Page Gamma" ou après le dernier header
            after_header = line[idx:]

            # Chercher la fin du header (après "Page Gamma" ou "LinkedIn")
            # et le début des vraies données (qui commencent par un nom d'entreprise)
            parts = after_header.split(pattern, 1) if idx == 0 else [after_header]

            # Stratégie : trouver le dernier header et prendre ce qui suit
            last_header_end = -1
            for hp in HEADER_PATTERNS:
                pos = line.lower().rfind(hp.lower())
                if pos > last_header_end:
                    # Trouver la fin de ce header (chercher "Page Gamma" après)
                    gamma_pos = line.lower().find("page gamma", pos)
                    if gamma_pos != -1:
                        # Les données commencent après "Page Gamma"
                        end_pos = gamma_pos + len("page gamma")
                        # Sauter les espaces et virgules
                        while end_pos < len(line) and line[end_pos] in " ,\t":
                            end_pos += 1
                        if end_pos > last_header_end:
                            last_header_end = end_pos

            if last_header_end > 0 and last_header_end < len(line):
                line = line[last_header_end:].strip()
                # Supprimer une virgule en début si présente
                if line.startswith(","):
                    line = line[1:].strip()

    # Si la ligne est juste un header, la rejeter
    for pattern in HEADER_PATTERNS:
        if line.lower().startswith(pattern.lower()) and "page gamma" in line.lower():
            # Vérifier si c'est UNIQUEMENT un header (pas de données après)
            gamma_pos = line.lower().find("page gamma")
            after_gamma = line[gamma_pos + len("page gamma"):].strip()
            if not after_gamma or after_gamma == "```":
                return None

    # Rejeter si la ligne est vide ou ne contient que des espaces
    if not line or line.isspace():
        return None

    return line


def merge_results_to_csv(
    results: list[UrlResult],
    output_path: Path,
    backup_dir: Path,
) -> None:
    """
    Fusionne les résultats en un CSV final (écrasement complet).

    Note: Cette fonction n'est plus utilisée par le mode parallèle qui
    sauvegarde désormais de manière incrémentale via append_result_to_csv.
    Elle est conservée pour un usage standalone (reconstruction manuelle
    d'un CSV à partir d'une liste de résultats).

    Args:
        results: Liste des résultats à fusionner
        output_path: Chemin du fichier CSV de sortie
        backup_dir: Dossier pour les backups
    """
    # Backup si le fichier existe
    if output_path.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"company_report_{timestamp}.csv"
        backup_path.write_text(output_path.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")

    # Collecter et nettoyer les lignes réussies
    rows = []
    for r in results:
        if r.status == RunStatus.SUCCESS and r.csv_row:
            cleaned = clean_csv_row(r.csv_row)
            if cleaned:
                rows.append(cleaned)

    # Écrire le fichier
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(CSV_HEADER + "\n")
        for row in rows:
            f.write(row + "\n")


def append_result_to_csv(
    result: UrlResult,
    output_path: Path,
) -> None:
    """
    Ajoute un résultat au CSV existant (mode incrémental).

    Crée le fichier avec header s'il n'existe pas.
    Ne recrée jamais le header si le fichier existe déjà.

    Args:
        result: Résultat à ajouter
        output_path: Chemin du fichier CSV
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Créer le fichier avec header UNIQUEMENT s'il n'existe pas
    if not output_path.exists():
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(CSV_HEADER + "\n")

    # Ajouter la ligne si succès (après nettoyage)
    if result.status == RunStatus.SUCCESS and result.csv_row:
        clean_row = clean_csv_row(result.csv_row)
        if clean_row:
            with open(output_path, "a", encoding="utf-8-sig", newline="") as f:
                f.write(clean_row + "\n")


async def run_sequential(
    urls: list[str],
    crew_class: Any,
    log_dir: Path,
    output_path: Path,
    timeout: int = 600,
    retry_count: int = 1,
    on_progress: Any = None,
) -> list[UrlResult]:
    """
    Exécute le crew pour chaque URL séquentiellement avec sauvegarde immédiate.

    Chaque URL est traitée une par une et le résultat est ajouté au CSV
    immédiatement après le traitement. En cas de crash, les URLs déjà
    traitées sont conservées.

    Args:
        urls: Liste des URLs à traiter
        crew_class: Classe du crew à instancier
        log_dir: Dossier pour les logs
        output_path: Chemin du fichier CSV de sortie
        timeout: Timeout par URL en secondes
        retry_count: Nombre de retry en cas d'échec
        on_progress: Callback optionnel appelé après chaque URL (index, total, result)

    Returns:
        Liste de UrlResult pour chaque URL
    """
    results: list[UrlResult] = []
    total = len(urls)

    # Créer le fichier de log TXT consolidé
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    consolidated_log_path = log_dir / f"run_{timestamp}.txt"

    def write_log(message: str) -> None:
        """Écrit dans le log consolidé et affiche à l'écran."""
        with open(consolidated_log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
        print(message)

    # Header du log
    write_log("=" * 70)
    write_log(f"WAKASTART LEADS - EXECUTION LOG")
    write_log(f"Démarré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    write_log(f"Nombre d'URLs: {total}")
    write_log(f"Timeout par URL: {timeout}s")
    write_log(f"Retry count: {retry_count}")
    write_log("=" * 70)
    write_log(f"\nINPUTS:")
    for i, url in enumerate(urls):
        write_log(f"  [{i + 1}] {url}")
    write_log("\n" + "=" * 70)

    for index, url in enumerate(urls):
        write_log(f"\n[{index + 1}/{total}] TRAITEMENT: {url}")
        write_log("-" * 50)
        start_time = datetime.now()

        # Retry logic
        last_result = None
        for attempt in range(retry_count + 1):
            if attempt > 0:
                write_log(f"  Tentative {attempt + 1}/{retry_count + 1}...")
            result = await run_single_url(url, crew_class, log_dir, timeout)
            if result.status == RunStatus.SUCCESS:
                break
            last_result = result
            if attempt < retry_count:
                wait_time = 2**attempt
                write_log(f"  ⚠️ Échec, retry dans {wait_time}s...")
                await asyncio.sleep(wait_time)
        else:
            result = last_result

        results.append(result)

        # Sauvegarde immédiate au CSV
        append_result_to_csv(result, output_path)

        # Log détaillé du résultat
        end_time = datetime.now()
        write_log(f"  Statut: {result.status.value.upper()}")
        write_log(f"  Durée: {result.duration_seconds:.1f}s")

        if result.status == RunStatus.SUCCESS:
            write_log(f"  ✅ CSV enrichi avec succès")
            if result.csv_row:
                # Extraire quelques infos clés du CSV row
                parts = result.csv_row.split(",")
                if len(parts) >= 6:
                    write_log(f"  OUTPUT:")
                    write_log(f"    - Société: {parts[0]}")
                    write_log(f"    - Nationalité: {parts[2] if len(parts) > 2 else 'N/A'}")
                    write_log(f"    - Année création: {parts[3] if len(parts) > 3 else 'N/A'}")
                    write_log(f"    - Pertinence: {parts[5] if len(parts) > 5 else 'N/A'}")
        elif result.status == RunStatus.TIMEOUT:
            write_log(f"  ⏱️ Timeout après {timeout}s")
        else:
            write_log(f"  ❌ Erreur: {result.error}")

        write_log(f"  Heure fin: {end_time.strftime('%H:%M:%S')}")

        # Callback de progression
        if on_progress:
            on_progress(index, total, result)

    # Résumé final
    success = sum(1 for r in results if r.status == RunStatus.SUCCESS)
    failed = sum(1 for r in results if r.status == RunStatus.FAILED)
    timeouts = sum(1 for r in results if r.status == RunStatus.TIMEOUT)

    write_log("\n" + "=" * 70)
    write_log("RÉSUMÉ FINAL")
    write_log("=" * 70)
    write_log(f"  Total URLs: {total}")
    write_log(f"  ✅ Succès: {success}")
    write_log(f"  ❌ Échecs: {failed}")
    write_log(f"  ⏱️ Timeouts: {timeouts}")
    write_log(f"\nFichier CSV: {output_path}")
    write_log(f"Fichier log: {consolidated_log_path}")
    write_log(f"Terminé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    write_log("=" * 70)

    return results