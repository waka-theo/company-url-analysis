"""Utilitaires pour la manipulation d'URLs."""

import json
from pathlib import Path


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


def load_urls(input_dir: Path, test_mode: bool = True) -> list[str]:
    """
    Load URLs from JSON file.

    Args:
        input_dir: Directory containing liste.json and liste_test.json
        test_mode: Use liste_test.json (True) or liste.json (False)

    Returns:
        List of URLs
    """
    filename = "liste_test.json" if test_mode else "liste.json"
    json_path = input_dir / filename

    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def ensure_https(url: str) -> str:
    """Assure que l'URL a un protocole https://"""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url
