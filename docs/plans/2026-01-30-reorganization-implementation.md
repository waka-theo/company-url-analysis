# Réorganisation Projet - Plan d'Implémentation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Réorganiser le projet en structure par crew isolé avec package renommé `wakastart_leads`

**Architecture:** Migration du package `company_url_analysis_automation` vers `wakastart_leads` avec 3 crews isolés (analysis, search, enrichment), tools partagés dans `shared/`, et utils extraits de main.py

**Tech Stack:** Python 3.10+, CrewAI, pytest

---

## Task 1: Créer la structure de dossiers

**Files:**
- Create: `src/wakastart_leads/` (nouveau package)
- Create: `src/wakastart_leads/crews/{analysis,search,enrichment}/`
- Create: `src/wakastart_leads/shared/{tools,utils}/`

**Step 1: Créer l'arborescence principale**

```bash
mkdir -p src/wakastart_leads/crews/analysis/config
mkdir -p src/wakastart_leads/crews/analysis/tools
mkdir -p src/wakastart_leads/crews/analysis/input
mkdir -p src/wakastart_leads/crews/analysis/output/logs
mkdir -p src/wakastart_leads/crews/analysis/output/backups
mkdir -p src/wakastart_leads/crews/search/config
mkdir -p src/wakastart_leads/crews/search/input
mkdir -p src/wakastart_leads/crews/search/output/logs
mkdir -p src/wakastart_leads/crews/enrichment/config
mkdir -p src/wakastart_leads/crews/enrichment/input
mkdir -p src/wakastart_leads/crews/enrichment/output/logs
mkdir -p src/wakastart_leads/crews/enrichment/output/backups
mkdir -p src/wakastart_leads/shared/tools
mkdir -p src/wakastart_leads/shared/utils
```

**Step 2: Vérifier la création**

Run: `find src/wakastart_leads -type d | head -20`
Expected: Liste des dossiers créés

**Step 3: Commit**

```bash
git add src/wakastart_leads/
git commit -m "chore: create wakastart_leads package structure"
```

---

## Task 2: Créer les fichiers __init__.py

**Files:**
- Create: Tous les `__init__.py` nécessaires

**Step 1: Créer les __init__.py**

```bash
# Package racine
touch src/wakastart_leads/__init__.py

# Crews
touch src/wakastart_leads/crews/__init__.py
touch src/wakastart_leads/crews/analysis/__init__.py
touch src/wakastart_leads/crews/analysis/tools/__init__.py
touch src/wakastart_leads/crews/search/__init__.py
touch src/wakastart_leads/crews/enrichment/__init__.py

# Shared
touch src/wakastart_leads/shared/__init__.py
touch src/wakastart_leads/shared/tools/__init__.py
touch src/wakastart_leads/shared/utils/__init__.py
```

**Step 2: Commit**

```bash
git add src/wakastart_leads/
git commit -m "chore: add __init__.py files"
```

---

## Task 3: Déplacer et adapter le crew Analysis

**Files:**
- Move: `src/company_url_analysis_automation/crew.py` → `src/wakastart_leads/crews/analysis/crew.py`
- Move: `src/company_url_analysis_automation/config/agents.yaml` → `src/wakastart_leads/crews/analysis/config/agents.yaml`
- Move: `src/company_url_analysis_automation/config/tasks.yaml` → `src/wakastart_leads/crews/analysis/config/tasks.yaml`
- Move: `src/company_url_analysis_automation/tools/gamma_tool.py` → `src/wakastart_leads/crews/analysis/tools/gamma_tool.py`
- Move: `src/company_url_analysis_automation/tools/kaspr_tool.py` → `src/wakastart_leads/crews/analysis/tools/kaspr_tool.py`
- Move: `liste.json`, `liste_test.json` → `src/wakastart_leads/crews/analysis/input/`
- Move: `docs/gamma_api.txt` → `src/wakastart_leads/crews/analysis/tools/gamma_api.txt`
- Move: `docs/kaspr.txt` → `src/wakastart_leads/crews/analysis/tools/kaspr_api.txt`

**Step 1: Copier les fichiers config**

```bash
cp src/company_url_analysis_automation/config/agents.yaml src/wakastart_leads/crews/analysis/config/
cp src/company_url_analysis_automation/config/tasks.yaml src/wakastart_leads/crews/analysis/config/
```

**Step 2: Copier les tools spécifiques**

```bash
cp src/company_url_analysis_automation/tools/gamma_tool.py src/wakastart_leads/crews/analysis/tools/
cp src/company_url_analysis_automation/tools/kaspr_tool.py src/wakastart_leads/crews/analysis/tools/
```

**Step 3: Copier les fichiers input**

```bash
cp liste.json src/wakastart_leads/crews/analysis/input/
cp liste_test.json src/wakastart_leads/crews/analysis/input/
```

**Step 4: Copier les docs API**

```bash
cp docs/gamma_api.txt src/wakastart_leads/crews/analysis/tools/
cp docs/kaspr.txt src/wakastart_leads/crews/analysis/tools/kaspr_api.txt
```

**Step 5: Copier et adapter crew.py**

Copier `src/company_url_analysis_automation/crew.py` vers `src/wakastart_leads/crews/analysis/crew.py` et modifier les imports :

```python
from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

from .tools.gamma_tool import GammaCreateTool
from .tools.kaspr_tool import KasprEnrichTool
from wakastart_leads.shared.tools.pappers_tool import PappersSearchTool


@CrewBase
class AnalysisCrew:
    """Analysis crew - Analyse complete des entreprises SaaS"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    log_file: str | None = None

    # ... reste du code identique, renommer la classe
```

**Step 6: Créer le __init__.py du tools analysis**

Écrire dans `src/wakastart_leads/crews/analysis/tools/__init__.py` :

```python
"""Tools spécifiques au crew Analysis."""

from .gamma_tool import GammaCreateTool
from .kaspr_tool import KasprEnrichTool

__all__ = ["GammaCreateTool", "KasprEnrichTool"]
```

**Step 7: Créer le __init__.py du crew analysis**

Écrire dans `src/wakastart_leads/crews/analysis/__init__.py` :

```python
"""Analysis crew - Analyse complete des entreprises SaaS."""

from .crew import AnalysisCrew

__all__ = ["AnalysisCrew"]
```

**Step 8: Mettre à jour output_file dans crew.py**

Dans `src/wakastart_leads/crews/analysis/crew.py`, modifier la tâche `compile_final_company_analysis_report` :

```python
output_file="src/wakastart_leads/crews/analysis/output/company_report_new.csv",
```

**Step 9: Commit**

```bash
git add src/wakastart_leads/crews/analysis/
git commit -m "feat: migrate analysis crew to new structure"
```

---

## Task 4: Déplacer et adapter le crew Search

**Files:**
- Move: `src/company_url_analysis_automation/search_crew.py` → `src/wakastart_leads/crews/search/crew.py`
- Move: `src/company_url_analysis_automation/config/search_agents.yaml` → `src/wakastart_leads/crews/search/config/agents.yaml`
- Move: `src/company_url_analysis_automation/config/search_tasks.yaml` → `src/wakastart_leads/crews/search/config/tasks.yaml`
- Move: `search_criteria.json` → `src/wakastart_leads/crews/search/input/`

**Step 1: Copier les fichiers config**

```bash
cp src/company_url_analysis_automation/config/search_agents.yaml src/wakastart_leads/crews/search/config/agents.yaml
cp src/company_url_analysis_automation/config/search_tasks.yaml src/wakastart_leads/crews/search/config/tasks.yaml
```

**Step 2: Copier le fichier input**

```bash
cp search_criteria.json src/wakastart_leads/crews/search/input/
```

**Step 3: Copier et adapter search_crew.py**

Copier vers `src/wakastart_leads/crews/search/crew.py` et modifier :

```python
"""Search crew for discovering SaaS company URLs from flexible search criteria."""

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

from wakastart_leads.shared.tools.pappers_tool import PappersSearchTool


@CrewBase
class SearchCrew:
    """SearchCrew - Decouvre des URLs d'entreprises SaaS a partir de criteres de recherche."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    log_file: str | None = None

    # ... reste identique, mettre à jour output_file
```

**Step 4: Mettre à jour output_file**

Dans la tâche `search_saas_deep_scan` :

```python
output_file="src/wakastart_leads/crews/search/output/search_results_raw.json",
```

**Step 5: Créer le __init__.py**

Écrire dans `src/wakastart_leads/crews/search/__init__.py` :

```python
"""Search crew - Découverte d'URLs d'entreprises SaaS."""

from .crew import SearchCrew

__all__ = ["SearchCrew"]
```

**Step 6: Commit**

```bash
git add src/wakastart_leads/crews/search/
git commit -m "feat: migrate search crew to new structure"
```

---

## Task 5: Déplacer et adapter le crew Enrichment

**Files:**
- Move: `src/company_url_analysis_automation/enrichment_crew.py` → `src/wakastart_leads/crews/enrichment/crew.py`
- Move: `src/company_url_analysis_automation/config/enrichment_agents.yaml` → `src/wakastart_leads/crews/enrichment/config/agents.yaml`
- Move: `src/company_url_analysis_automation/config/enrichment_tasks.yaml` → `src/wakastart_leads/crews/enrichment/config/tasks.yaml`

**Step 1: Copier les fichiers config**

```bash
cp src/company_url_analysis_automation/config/enrichment_agents.yaml src/wakastart_leads/crews/enrichment/config/agents.yaml
cp src/company_url_analysis_automation/config/enrichment_tasks.yaml src/wakastart_leads/crews/enrichment/config/tasks.yaml
```

**Step 2: Copier et adapter enrichment_crew.py**

Copier vers `src/wakastart_leads/crews/enrichment/crew.py` :

```python
"""Enrichment crew for analyzing and scoring companies for WakaStart relevance."""

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool


@CrewBase
class EnrichmentCrew:
    """EnrichmentCrew - Enrichit les donnees d'entreprises."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    log_file: str | None = None

    # ... reste identique
```

**Step 3: Créer .gitkeep pour input**

```bash
touch src/wakastart_leads/crews/enrichment/input/.gitkeep
```

**Step 4: Créer le __init__.py**

Écrire dans `src/wakastart_leads/crews/enrichment/__init__.py` :

```python
"""Enrichment crew - Enrichissement des données d'entreprises."""

from .crew import EnrichmentCrew

__all__ = ["EnrichmentCrew"]
```

**Step 5: Commit**

```bash
git add src/wakastart_leads/crews/enrichment/
git commit -m "feat: migrate enrichment crew to new structure"
```

---

## Task 6: Créer le module shared/tools

**Files:**
- Move: `src/company_url_analysis_automation/tools/pappers_tool.py` → `src/wakastart_leads/shared/tools/pappers_tool.py`
- Move: `docs/pappers_api_v2.yaml` → `src/wakastart_leads/shared/tools/pappers_api.yaml`

**Step 1: Copier pappers_tool.py**

```bash
cp src/company_url_analysis_automation/tools/pappers_tool.py src/wakastart_leads/shared/tools/
```

**Step 2: Copier la doc API**

```bash
cp docs/pappers_api_v2.yaml src/wakastart_leads/shared/tools/pappers_api.yaml
```

**Step 3: Créer le __init__.py**

Écrire dans `src/wakastart_leads/shared/tools/__init__.py` :

```python
"""Tools partagés entre plusieurs crews."""

from .pappers_tool import PappersSearchTool

__all__ = ["PappersSearchTool"]
```

**Step 4: Commit**

```bash
git add src/wakastart_leads/shared/tools/
git commit -m "feat: add shared tools module with pappers_tool"
```

---

## Task 7: Créer le module shared/utils

**Files:**
- Create: `src/wakastart_leads/shared/utils/url_utils.py`
- Create: `src/wakastart_leads/shared/utils/csv_utils.py`
- Create: `src/wakastart_leads/shared/utils/log_rotation.py`
- Create: `src/wakastart_leads/shared/utils/constants.py`

**Step 1: Créer url_utils.py**

Écrire dans `src/wakastart_leads/shared/utils/url_utils.py` :

```python
"""Utilitaires pour la manipulation d'URLs."""

import json
import os
from pathlib import Path


def normalize_url(url: str) -> str:
    """Normalise une URL pour la deduplication (protocole, www, trailing slash, casse)."""
    url = url.strip().lower().rstrip("/")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
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
```

**Step 2: Créer csv_utils.py**

Écrire dans `src/wakastart_leads/shared/utils/csv_utils.py` :

```python
"""Utilitaires pour la manipulation de fichiers CSV."""

import csv
import io
import os
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
            row.extend(["Non trouvé"] * (expected_columns - len(row)))

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
            row.extend(["Non trouvé"] * (expected_columns - len(row)))
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
```

**Step 3: Créer log_rotation.py**

Écrire dans `src/wakastart_leads/shared/utils/log_rotation.py` :

```python
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
        [f for f in logs_dir.iterdir() if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,  # Plus recent en premier
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
```

**Step 4: Créer constants.py**

Écrire dans `src/wakastart_leads/shared/utils/constants.py` :

```python
"""Constantes partagées du projet."""

from pathlib import Path

# Racine du package
PACKAGE_ROOT = Path(__file__).parent.parent.parent

# Chemins des crews
ANALYSIS_DIR = PACKAGE_ROOT / "crews" / "analysis"
SEARCH_DIR = PACKAGE_ROOT / "crews" / "search"
ENRICHMENT_DIR = PACKAGE_ROOT / "crews" / "enrichment"

# Chemins input/output par crew
ANALYSIS_INPUT = ANALYSIS_DIR / "input"
ANALYSIS_OUTPUT = ANALYSIS_DIR / "output"
SEARCH_INPUT = SEARCH_DIR / "input"
SEARCH_OUTPUT = SEARCH_DIR / "output"
ENRICHMENT_INPUT = ENRICHMENT_DIR / "input"
ENRICHMENT_OUTPUT = ENRICHMENT_DIR / "output"

# Fichiers par defaut
ANALYSIS_CSV_FINAL = ANALYSIS_OUTPUT / "company_report.csv"
ANALYSIS_CSV_NEW = ANALYSIS_OUTPUT / "company_report_new.csv"
SEARCH_RAW_OUTPUT = SEARCH_OUTPUT / "search_results_raw.json"
ENRICHMENT_ACCUMULATED = ENRICHMENT_OUTPUT / "enrichment_accumulated.json"

# Configuration
EXPECTED_COLUMNS = 23
URL_COLUMN_INDEX = 1
DEFAULT_BATCH_SIZE = 20
```

**Step 5: Créer le __init__.py de utils**

Écrire dans `src/wakastart_leads/shared/utils/__init__.py` :

```python
"""Utilitaires partagés."""

from .constants import (
    ANALYSIS_DIR,
    ANALYSIS_INPUT,
    ANALYSIS_OUTPUT,
    ENRICHMENT_DIR,
    ENRICHMENT_INPUT,
    ENRICHMENT_OUTPUT,
    EXPECTED_COLUMNS,
    PACKAGE_ROOT,
    SEARCH_DIR,
    SEARCH_INPUT,
    SEARCH_OUTPUT,
    URL_COLUMN_INDEX,
)
from .csv_utils import clean_markdown_artifacts, load_existing_csv, post_process_csv
from .log_rotation import cleanup_old_logs, get_log_retention_days
from .url_utils import ensure_https, load_urls, normalize_url

__all__ = [
    # URL utils
    "normalize_url",
    "load_urls",
    "ensure_https",
    # CSV utils
    "load_existing_csv",
    "post_process_csv",
    "clean_markdown_artifacts",
    # Log rotation
    "cleanup_old_logs",
    "get_log_retention_days",
    # Constants
    "PACKAGE_ROOT",
    "ANALYSIS_DIR",
    "ANALYSIS_INPUT",
    "ANALYSIS_OUTPUT",
    "SEARCH_DIR",
    "SEARCH_INPUT",
    "SEARCH_OUTPUT",
    "ENRICHMENT_DIR",
    "ENRICHMENT_INPUT",
    "ENRICHMENT_OUTPUT",
    "EXPECTED_COLUMNS",
    "URL_COLUMN_INDEX",
]
```

**Step 6: Commit**

```bash
git add src/wakastart_leads/shared/utils/
git commit -m "feat: add shared utils module (url, csv, log_rotation, constants)"
```

---

## Task 8: Créer le nouveau main.py

**Files:**
- Create: `src/wakastart_leads/main.py`

**Step 1: Créer main.py**

Écrire dans `src/wakastart_leads/main.py` le point d'entrée simplifié utilisant les nouveaux modules :

```python
#!/usr/bin/env python
"""Point d'entrée CLI pour WakaStart Leads."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from wakastart_leads.crews.analysis import AnalysisCrew
from wakastart_leads.crews.enrichment import EnrichmentCrew
from wakastart_leads.crews.search import SearchCrew
from wakastart_leads.shared.utils import (
    ANALYSIS_INPUT,
    ANALYSIS_OUTPUT,
    ENRICHMENT_OUTPUT,
    SEARCH_INPUT,
    SEARCH_OUTPUT,
    cleanup_old_logs,
    load_urls,
    normalize_url,
    post_process_csv,
)


def _setup_log_file(crew_output_dir: Path, workflow: str) -> str:
    """Cree le dossier de logs et retourne le chemin du fichier de log."""
    log_dir = crew_output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{workflow}_{timestamp}.json"
    return str(log_path)


def run():
    """Run the analysis crew."""
    urls = load_urls(ANALYSIS_INPUT)
    inputs = {"urls": urls}

    crew_instance = AnalysisCrew()
    crew_instance.log_file = _setup_log_file(ANALYSIS_OUTPUT, "run")
    print(f"[INFO] Logs: {crew_instance.log_file}")

    crew_instance.crew().kickoff(inputs=inputs)

    post_process_csv(
        new_csv_path=ANALYSIS_OUTPUT / "company_report_new.csv",
        final_csv_path=ANALYSIS_OUTPUT / "company_report.csv",
        backup_dir=ANALYSIS_OUTPUT / "backups",
    )

    # Rotation des logs
    cleanup_old_logs(ANALYSIS_OUTPUT / "logs")


def search():
    """Search for SaaS company URLs based on criteria."""
    import argparse

    parser = argparse.ArgumentParser(description="Search for SaaS company URLs")
    parser.add_argument("--criteria", type=str, help="Path to JSON criteria file")
    parser.add_argument("--output", type=str, help="Output file path")

    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    # Charger les criteres
    criteria_path = Path(args.criteria) if args.criteria else SEARCH_INPUT / "search_criteria.json"

    with open(criteria_path, encoding="utf-8") as f:
        criteria = json.load(f)

    # Formater pour l'agent
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

    # Post-process et rotation
    _post_process_search_results(args.output)
    cleanup_old_logs(SEARCH_OUTPUT / "logs")


def enrich():
    """Enrich company CSV with WakaStart analysis."""
    import argparse
    import csv
    import io

    parser = argparse.ArgumentParser(description="Enrich company CSV")
    parser.add_argument("--input", "-i", type=str, default="Datas entreprises Tom - Affinage n°6.csv")
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--batch-size", "-b", type=int, default=20)
    parser.add_argument("--test", action="store_true")

    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    # Charger le CSV
    input_path = Path(args.input)
    if not input_path.is_absolute():
        # Chercher dans enrichment/input ou a la racine du projet
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

    # Extraire URLs
    all_urls = _extract_urls_from_csv(rows)

    if args.test:
        all_urls = all_urls[:20]
        print(f"[INFO] Mode test: {len(all_urls)} URL(s)")

    if not all_urls:
        print("[WARNING] Aucune URL a traiter")
        return

    # Charger resultats existants
    accumulated_file = ENRICHMENT_OUTPUT / "enrichment_accumulated.json"
    all_enrichments, processed_urls = _load_accumulated_results(accumulated_file)

    # Filtrer URLs deja traitees
    urls_to_process = [url for url in all_urls if normalize_url(url) not in processed_urls]
    print(f"[INFO] {len(urls_to_process)} URL(s) restante(s)")

    if urls_to_process:
        # Traiter par batches
        batch_size = args.batch_size
        for i in range(0, len(urls_to_process), batch_size):
            batch = urls_to_process[i:i + batch_size]
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

            # Sauvegarder
            with open(accumulated_file, "w", encoding="utf-8") as f:
                json.dump(all_enrichments, f, ensure_ascii=False, indent=2)

    # Mettre a jour CSV
    rows = _update_csv_with_enrichment(rows, all_enrichments)

    # Sauvegarder
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

    # Rotation
    cleanup_old_logs(ENRICHMENT_OUTPUT / "logs")


# Fonctions helper privees
def _format_search_criteria(criteria: dict) -> str:
    parts = []
    if criteria.get("keywords"):
        kw = criteria["keywords"]
        parts.append(f"Mots-cles: {', '.join(kw) if isinstance(kw, list) else kw}")
    if criteria.get("sector"):
        parts.append(f"Secteur: {criteria['sector']}")
    if criteria.get("geographic_zone"):
        parts.append(f"Zone: {criteria['geographic_zone']}")
    return "\n".join(parts) if parts else "Recherche large SaaS France"


def _post_process_search_results(output_path: str | None) -> list[str]:
    raw_path = SEARCH_OUTPUT / "search_results_raw.json"
    if not raw_path.exists():
        return []

    with open(raw_path, encoding="utf-8") as f:
        content = f.read().strip()

    # Nettoyage markdown
    if content.startswith("```"):
        lines = [l for l in content.splitlines() if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        urls = json.loads(content)
    except json.JSONDecodeError:
        return []

    # Deduplication
    seen = set()
    final_urls = []
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

    # Ecrire
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
    urls = []
    for row in rows:
        url = row.get("Site Internet", "").strip()
        if not url or (" " in url and not url.startswith("http")):
            continue
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        urls.append(url)
    return urls


def _load_accumulated_results(path: Path) -> tuple[list[dict], set[str]]:
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
    import re
    if not raw:
        return []
    content = raw.strip()
    lines = [l for l in content.splitlines() if not l.strip().startswith("```")]
    content = "\n".join(lines).strip()
    if not content.startswith("["):
        match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if match:
            content = match.group(0)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return []


def _update_csv_with_enrichment(rows: list[dict], enrichments: list[dict]) -> list[dict]:
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
            row["Nationalité"] = e.get("nationalite", "")
            row["Solution Saas"] = e.get("solution_saas", "")
            row["Pertinance"] = e.get("pertinence", "")
            row["Explication"] = e.get("explication", "")
    return rows


def train():
    """Train the crew."""
    urls = load_urls(ANALYSIS_INPUT)
    AnalysisCrew().crew().train(n_iterations=int(sys.argv[2]), filename=sys.argv[3], inputs={"urls": urls})


def replay():
    """Replay from a specific task."""
    AnalysisCrew().crew().replay(task_id=sys.argv[2])


def test():
    """Test the crew."""
    urls = load_urls(ANALYSIS_INPUT)
    AnalysisCrew().crew().test(n_iterations=int(sys.argv[2]), openai_model_name=sys.argv[3], inputs={"urls": urls})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m wakastart_leads.main <command>")
        print("Commands: run, search, enrich, train, replay, test")
        sys.exit(1)

    command = sys.argv[1]
    commands = {"run": run, "search": search, "enrich": enrich, "train": train, "replay": replay, "test": test}

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
```

**Step 2: Commit**

```bash
git add src/wakastart_leads/main.py
git commit -m "feat: add new main.py entry point"
```

---

## Task 9: Créer le __init__.py principal et crews/__init__.py

**Files:**
- Modify: `src/wakastart_leads/__init__.py`
- Modify: `src/wakastart_leads/crews/__init__.py`

**Step 1: Écrire __init__.py principal**

```python
"""WakaStart Leads - Multi-agent system for SaaS lead sourcing and enrichment."""

__version__ = "0.1.0"
```

**Step 2: Écrire crews/__init__.py**

```python
"""Crews disponibles."""

from .analysis import AnalysisCrew
from .enrichment import EnrichmentCrew
from .search import SearchCrew

__all__ = ["AnalysisCrew", "SearchCrew", "EnrichmentCrew"]
```

**Step 3: Commit**

```bash
git add src/wakastart_leads/__init__.py src/wakastart_leads/crews/__init__.py
git commit -m "feat: add package exports"
```

---

## Task 10: Mettre à jour pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Modifier pyproject.toml**

```toml
[project]
name = "wakastart_leads"
version = "0.1.0"
description = "Multi-agent system for SaaS lead sourcing and enrichment"
authors = [{ name = "Your Name", email = "you@example.com" }]
requires-python = ">=3.10,<3.14"
dependencies = [
    "anthropic>=0.76.0",
    "crewai[google-genai,litellm,tools]==1.7.2",
    "google-generativeai>=0.8.6",
    "python-docx>=1.2.0",
]

[project.scripts]
wakastart = "wakastart_leads.main:run"
wakastart-run = "wakastart_leads.main:run"
wakastart-search = "wakastart_leads.main:search"
wakastart-enrich = "wakastart_leads.main:enrich"
wakastart-train = "wakastart_leads.main:train"
wakastart-replay = "wakastart_leads.main:replay"
wakastart-test = "wakastart_leads.main:test"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wakastart_leads"]

[tool.crewai]
type = "crew"

[dependency-groups]
dev = [
    "ruff>=0.14.14",
    "pytest>=8.0",
    "pytest-mock>=3.14",
    "pytest-cov>=7.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "TCH", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["wakastart_leads"]
```

**Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: update pyproject.toml for wakastart_leads package"
```

---

## Task 11: Réorganiser les tests

**Files:**
- Create: `tests/crews/`, `tests/shared/`
- Move: Tests existants vers nouvelle structure

**Step 1: Créer la structure des tests**

```bash
mkdir -p tests/crews/analysis/tools
mkdir -p tests/crews/search
mkdir -p tests/crews/enrichment
mkdir -p tests/shared/tools
mkdir -p tests/integration
```

**Step 2: Créer les __init__.py**

```bash
touch tests/crews/__init__.py
touch tests/crews/analysis/__init__.py
touch tests/crews/analysis/tools/__init__.py
touch tests/crews/search/__init__.py
touch tests/crews/enrichment/__init__.py
touch tests/shared/__init__.py
touch tests/shared/tools/__init__.py
```

**Step 3: Déplacer les tests existants**

```bash
# Tests des tools analysis
cp tests/tools/test_gamma_tool.py tests/crews/analysis/tools/
cp tests/tools/test_kaspr_tool.py tests/crews/analysis/tools/

# Test pappers (shared)
cp tests/tools/test_pappers_tool.py tests/shared/tools/

# Tests crews
cp tests/test_crew_config.py tests/crews/analysis/test_crew.py
cp tests/test_search_crew.py tests/crews/search/test_crew.py

# Integration
cp tests/integration/test_gamma_integration.py tests/integration/
```

**Step 4: Mettre à jour les imports dans les tests**

Dans chaque fichier de test, remplacer :
- `from company_url_analysis_automation.` → `from wakastart_leads.`
- `from company_url_analysis_automation.tools.` → `from wakastart_leads.crews.analysis.tools.` ou `from wakastart_leads.shared.tools.`

**Step 5: Commit**

```bash
git add tests/
git commit -m "test: reorganize tests to match new structure"
```

---

## Task 12: Mettre à jour CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Mettre à jour les chemins et commandes dans CLAUDE.md**

Remplacer toutes les références à l'ancienne structure par la nouvelle :
- `src/company_url_analysis_automation/` → `src/wakastart_leads/`
- `src/.../crew.py` → `src/wakastart_leads/crews/analysis/crew.py`
- etc.

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with new project structure"
```

---

## Task 13: Copier les données existantes

**Files:**
- Copy: `output/company_report.csv` → `src/wakastart_leads/crews/analysis/output/`
- Copy: `output/enrichment_accumulated.json` → `src/wakastart_leads/crews/enrichment/output/`

**Step 1: Copier les données si elles existent**

```bash
# Analysis output
cp -r output/company_report.csv src/wakastart_leads/crews/analysis/output/ 2>/dev/null || true
cp -r output/backups/* src/wakastart_leads/crews/analysis/output/backups/ 2>/dev/null || true

# Enrichment output
cp output/enrichment_accumulated.json src/wakastart_leads/crews/enrichment/output/ 2>/dev/null || true

# Search output (logs)
cp -r output/logs/search/* src/wakastart_leads/crews/search/output/logs/ 2>/dev/null || true
```

**Step 2: Vérifier**

```bash
ls -la src/wakastart_leads/crews/*/output/
```

**Step 3: Commit**

```bash
git add src/wakastart_leads/crews/*/output/
git commit -m "chore: migrate existing output data to new structure"
```

---

## Task 14: Réorganiser docs/

**Files:**
- Create: `docs/business/`, `docs/guides/`
- Move: PDFs et guides

**Step 1: Créer les dossiers**

```bash
mkdir -p docs/business
mkdir -p docs/guides
```

**Step 2: Déplacer les fichiers**

```bash
mv "docs/Projet WakaStart.pdf" docs/business/ 2>/dev/null || true
mv "docs/Protocole Théo.pdf" docs/business/ 2>/dev/null || true
mv docs/agent-commercial.md docs/guides/ 2>/dev/null || true
```

**Step 3: Commit**

```bash
git add docs/
git commit -m "docs: reorganize documentation folders"
```

---

## Task 15: Nettoyer l'ancienne structure

**Files:**
- Delete: `src/company_url_analysis_automation/`
- Delete: `liste.json`, `liste_test.json`, `search_criteria.json` (à la racine)
- Delete: `output/` (à la racine)
- Delete: Anciens tests

**Step 1: Supprimer l'ancien package**

```bash
rm -rf src/company_url_analysis_automation/
```

**Step 2: Supprimer les fichiers racine déplacés**

```bash
rm -f liste.json liste_test.json search_criteria.json
```

**Step 3: Supprimer l'ancien output**

```bash
rm -rf output/
```

**Step 4: Supprimer les anciens tests**

```bash
rm -rf tests/tools/
rm -f tests/test_main.py tests/test_crew_config.py tests/test_search_crew.py tests/test_search_main.py
```

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove old structure after migration"
```

---

## Task 16: Vérifier que pytest passe

**Step 1: Réinstaller le package**

```bash
uv pip install -e .
```

**Step 2: Lancer les tests**

Run: `pytest -v`
Expected: Tous les tests passent (ou échecs liés aux imports à corriger)

**Step 3: Corriger les imports si nécessaire**

Si des tests échouent à cause d'imports, les corriger un par un.

**Step 4: Commit final**

```bash
git add -A
git commit -m "test: fix imports after reorganization"
```

---

## Task 17: Mettre à jour .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Adapter .gitignore pour les nouveaux chemins output**

```gitignore
.env
__pycache__/
.DS_Store
.serena/
.venv/
.coverage

# Outputs des crews (ignorés)
src/wakastart_leads/crews/*/output/logs/
src/wakastart_leads/crews/*/output/backups/
src/wakastart_leads/crews/*/output/*.csv
src/wakastart_leads/crews/*/output/*.json

# Garder les fichiers input
!src/wakastart_leads/crews/*/input/

# Tests
tests/__pycache__/

# Docs business (PDFs volumineux)
docs/business/
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for new structure"
```

---

## Summary

| Task | Description | Commits |
|------|-------------|---------|
| 1 | Créer structure dossiers | 1 |
| 2 | Créer __init__.py | 1 |
| 3 | Migrer crew Analysis | 1 |
| 4 | Migrer crew Search | 1 |
| 5 | Migrer crew Enrichment | 1 |
| 6 | Créer shared/tools | 1 |
| 7 | Créer shared/utils | 1 |
| 8 | Créer nouveau main.py | 1 |
| 9 | Exports packages | 1 |
| 10 | Mettre à jour pyproject.toml | 1 |
| 11 | Réorganiser tests | 1 |
| 12 | Mettre à jour CLAUDE.md | 1 |
| 13 | Copier données existantes | 1 |
| 14 | Réorganiser docs/ | 1 |
| 15 | Nettoyer ancienne structure | 1 |
| 16 | Vérifier pytest | 1 |
| 17 | Mettre à jour .gitignore | 1 |

**Total : 17 tâches, ~17 commits**
