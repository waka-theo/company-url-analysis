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

    Returns:
        Liste de UrlResult pour chaque URL
    """
    semaphore = asyncio.Semaphore(max_workers)

    async def run_with_retry(url: str) -> UrlResult:
        async with semaphore:
            last_result = None
            for attempt in range(retry_count + 1):
                result = await run_single_url(url, crew_class, log_dir, timeout)
                if result.status == RunStatus.SUCCESS:
                    return result
                last_result = result
                if attempt < retry_count:
                    await asyncio.sleep(2**attempt)  # Backoff exponentiel
            return last_result

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


def merge_results_to_csv(
    results: list[UrlResult],
    output_path: Path,
    backup_dir: Path,
) -> None:
    """
    Fusionne les résultats en un CSV final.

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

    # Collecter les lignes réussies
    rows = [
        r.csv_row
        for r in results
        if r.status == RunStatus.SUCCESS and r.csv_row
    ]

    # Écrire le fichier
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(CSV_HEADER + "\n")
        for row in rows:
            # Nettoyer la ligne (supprimer les retours à la ligne internes)
            clean_row = row.strip().replace("\n", " ").replace("\r", "")
            if clean_row:
                f.write(clean_row + "\n")


def append_result_to_csv(
    result: UrlResult,
    output_path: Path,
) -> None:
    """
    Ajoute un résultat au CSV existant (mode incrémental).

    Crée le fichier avec header s'il n'existe pas.

    Args:
        result: Résultat à ajouter
        output_path: Chemin du fichier CSV
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Créer le fichier avec header s'il n'existe pas
    if not output_path.exists():
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(CSV_HEADER + "\n")

    # Ajouter la ligne si succès
    if result.status == RunStatus.SUCCESS and result.csv_row:
        clean_row = result.csv_row.strip().replace("\n", " ").replace("\r", "")
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

    for index, url in enumerate(urls):
        print(f"\n[{index + 1}/{total}] Traitement de {url}")

        # Retry logic
        last_result = None
        for attempt in range(retry_count + 1):
            result = await run_single_url(url, crew_class, log_dir, timeout)
            if result.status == RunStatus.SUCCESS:
                break
            last_result = result
            if attempt < retry_count:
                wait_time = 2**attempt
                print(f"  ⚠️ Échec, retry dans {wait_time}s...")
                await asyncio.sleep(wait_time)
        else:
            result = last_result

        results.append(result)

        # Sauvegarde immédiate au CSV
        append_result_to_csv(result, output_path)

        # Afficher le statut
        if result.status == RunStatus.SUCCESS:
            print(f"  ✅ Succès ({result.duration_seconds:.1f}s)")
        elif result.status == RunStatus.TIMEOUT:
            print(f"  ⏱️ Timeout après {timeout}s")
        else:
            print(f"  ❌ Échec: {result.error}")

        # Callback de progression
        if on_progress:
            on_progress(index, total, result)

    return results