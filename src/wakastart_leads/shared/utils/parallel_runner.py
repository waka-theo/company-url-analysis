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