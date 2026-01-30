"""Utilitaires pour la rotation automatique des logs."""

import os
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_old_logs(
    logs_dir: Path,
    max_age_days: int = 30,
    min_keep: int = 5,
) -> int:
    """
    Supprime les fichiers de logs plus vieux que max_age_days.
    Garde toujours au minimum min_keep fichiers.

    Args:
        logs_dir: Dossier contenant les logs
        max_age_days: Age maximum en jours (defaut: 30)
        min_keep: Nombre minimum de fichiers a conserver (defaut: 5)

    Returns:
        Nombre de fichiers supprimes
    """
    if not logs_dir.exists():
        return 0

    # Lister tous les fichiers de log
    log_files = sorted(
        [f for f in logs_dir.iterdir() if f.is_file() and f.name != ".gitkeep"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if len(log_files) <= min_keep:
        return 0

    # Calculer la date limite
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0

    # Parcourir les fichiers (en gardant les min_keep premiers)
    for log_file in log_files[min_keep:]:
        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if file_mtime < cutoff_date:
            try:
                log_file.unlink()
                deleted_count += 1
            except OSError:
                pass

    if deleted_count > 0:
        print(f"[INFO] {deleted_count} ancien(s) log(s) supprime(s) dans {logs_dir}")

    return deleted_count


def get_log_retention_days() -> int:
    """Retourne le nombre de jours de retention depuis l'env ou 30 par defaut."""
    return int(os.environ.get("LOG_RETENTION_DAYS", "30"))
