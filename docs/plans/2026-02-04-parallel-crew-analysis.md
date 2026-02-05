# Parallélisation du Crew Analysis - Plan d'Implémentation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transformer le crew Analysis pour traiter chaque URL individuellement avec parallélisation configurable (1 URL = 1 run complet du crew).

**Architecture:** Créer un orchestrateur asyncio (`parallel_runner.py`) qui exécute N instances du crew en parallèle via un semaphore. Modifier les fichiers YAML pour traiter `{url}` au singulier. Conserver le mode `--batch` pour la rétrocompatibilité.

**Tech Stack:** Python 3.10+, asyncio, CrewAI 1.7.2, pytest

---

## Task 1: Modifier tasks.yaml pour traiter une URL unique

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/config/tasks.yaml:1-52`

**Step 1: Lire le fichier actuel**

Vérifier le contenu actuel de la task `extraction_and_macro_filtering`.

**Step 2: Remplacer {urls} par {url} dans extraction_and_macro_filtering**

```yaml
extraction_and_macro_filtering:
  description: |-
    Traiter l'URL fournie : {url}

    ACT 0 - Extraction & Ingestion :
    1. Vérifier que l'URL est valide et accessible
    2. Formater et normaliser l'URL

    ACT 1 - Extraction & Filtrage Macro :
    1. Vérifier que l'URL est accessible et valide
    2. Scraper le contenu du site pour extraire le nom de l'entreprise
    3. Confirmer le secteur d'activité (Édition logiciels, Conseil informatique, mais rester ouvert aux pivotages)
    4. Critère "SaaS Caché" : Ne pas s'arrêter à la vitrine. Chercher des indices de développement interne :
       - Offres d'emploi "Dev Fullstack" ou similaires
       - Mention de "Plateforme client", "Portail adhérent", "Espace membre"
       - Levées de fonds mentionnant "R&D", "tech", "plateforme"
       - Page "Produit", "Solution", "Tarifs" suggérant un modèle SaaS
    5. Noter si l'URL n'est pas accessible

    ACT 1-BIS - EXTRACTION SIREN (OBLIGATOIRE) :
    Pour l'entreprise identifiée, récupérer le numéro SIREN depuis les mentions légales :
    1. Scraper la page "Mentions légales" du site. Chemins à tester dans l'ordre :
       - /mentions-legales
       - /mentions-legales/
       - /legal
       - /cgv
       - /cgu
       - Chercher un lien "Mentions légales" dans le footer de la page d'accueil
    2. Chercher le numéro SIREN dans le contenu (9 chiffres consécutifs ou espacés)
       Patterns à détecter : "SIREN : XXX XXX XXX", "SIREN: XXXXXXXXX", "RCS [Ville] XXX XXX XXX",
       "N° SIREN", "Immatriculation", "Numéro d'identification"
    3. Si le SIREN n'est pas trouvé dans les mentions légales, chercher dans :
       - Page "À propos" / "Qui sommes-nous"
       - Page "Contact"
       - Conditions générales (CGV/CGU)
    4. IMPORTANT : Le SIREN est CRITIQUE pour identifier correctement l'entreprise.
       Il permet d'éviter les confusions avec des homonymes lors de la recherche Pappers.

    Exemple de référence : France-Care.fr (Service de conciergerie -> Développement d'un CRM métier après levée de fonds)
  expected_output: >
    Une structure pour l'URL contenant :
    - URL originale
    - Statut de validation (valid/invalid)
    - Nom de l'entreprise extrait
    - SIREN extrait (9 chiffres, format XXX XXX XXX) ou "Non trouvé" si introuvable
    - Indices SaaS détectés (liste des signaux trouvés ou "Aucun indice SaaS" si rien détecté)
    - Secteur d'activité apparent

    Format clair indiquant si l'URL a été traitée avec succès ou avec problèmes.
    Le SIREN est OBLIGATOIRE pour les agents suivants - ne jamais l'omettre.
  agent: economic_intelligence_analyst
```

**Step 3: Vérifier la syntaxe YAML**

Run: `python -c "import yaml; yaml.safe_load(open('src/wakastart_leads/crews/analysis/config/tasks.yaml'))"`
Expected: Pas d'erreur

**Step 4: Commit**

```bash
git add src/wakastart_leads/crews/analysis/config/tasks.yaml
git commit -m "refactor: change tasks.yaml to handle single URL instead of list"
```

---

## Task 2: Modifier agents.yaml pour traiter une URL unique

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/config/agents.yaml`

**Step 1: Lire le fichier actuel**

Chercher toute mention de `{urls}` dans le fichier.

**Step 2: Remplacer {urls} par {url} si présent**

Dans le goal de `economic_intelligence_analyst`, remplacer toute mention de "URLs" ou "{urls}" par "URL" ou "{url}".

**Step 3: Vérifier la syntaxe YAML**

Run: `python -c "import yaml; yaml.safe_load(open('src/wakastart_leads/crews/analysis/config/agents.yaml'))"`
Expected: Pas d'erreur

**Step 4: Commit**

```bash
git add src/wakastart_leads/crews/analysis/config/agents.yaml
git commit -m "refactor: change agents.yaml to handle single URL"
```

---

## Task 3: Créer le module parallel_runner.py - Structures de données

**Files:**
- Create: `src/wakastart_leads/shared/utils/parallel_runner.py`
- Test: `tests/shared/utils/test_parallel_runner.py`

**Step 1: Écrire le test pour les structures de données**

```python
# tests/shared/utils/test_parallel_runner.py
"""Tests pour le module parallel_runner."""

import pytest

from wakastart_leads.shared.utils.parallel_runner import RunStatus, UrlResult


class TestRunStatus:
    def test_status_values(self):
        """Vérifie les valeurs des statuts."""
        assert RunStatus.SUCCESS.value == "success"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.TIMEOUT.value == "timeout"


class TestUrlResult:
    def test_create_success_result(self):
        """Crée un résultat de succès."""
        result = UrlResult(
            url="https://example.com",
            status=RunStatus.SUCCESS,
            csv_row="Example,https://example.com,FR,2020",
            error=None,
            duration_seconds=15.5,
        )
        assert result.url == "https://example.com"
        assert result.status == RunStatus.SUCCESS
        assert result.csv_row is not None
        assert result.error is None

    def test_create_failed_result(self):
        """Crée un résultat d'échec."""
        result = UrlResult(
            url="https://broken.com",
            status=RunStatus.FAILED,
            csv_row=None,
            error="Connection timeout",
            duration_seconds=30.0,
        )
        assert result.status == RunStatus.FAILED
        assert result.csv_row is None
        assert "timeout" in result.error.lower()
```

**Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `pytest tests/shared/utils/test_parallel_runner.py -v`
Expected: FAIL avec "ModuleNotFoundError" ou "ImportError"

**Step 3: Implémenter les structures de données**

```python
# src/wakastart_leads/shared/utils/parallel_runner.py
"""Module d'orchestration parallèle pour le traitement des URLs."""

from dataclasses import dataclass
from enum import Enum


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
```

**Step 4: Lancer le test pour vérifier qu'il passe**

Run: `pytest tests/shared/utils/test_parallel_runner.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/wakastart_leads/shared/utils/parallel_runner.py tests/shared/utils/test_parallel_runner.py
git commit -m "feat: add parallel_runner module with data structures"
```

---

## Task 4: Implémenter run_single_url

**Files:**
- Modify: `src/wakastart_leads/shared/utils/parallel_runner.py`
- Modify: `tests/shared/utils/test_parallel_runner.py`

**Step 1: Écrire le test pour run_single_url**

```python
# Ajouter à tests/shared/utils/test_parallel_runner.py

from unittest.mock import MagicMock, patch
import asyncio

from wakastart_leads.shared.utils.parallel_runner import run_single_url


class TestRunSingleUrl:
    @pytest.mark.asyncio
    async def test_success_execution(self, tmp_path):
        """Test exécution réussie d'une URL."""
        mock_crew_class = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance
        mock_crew_instance.crew.return_value.kickoff.return_value = MagicMock(raw="CSV,row,data")

        result = await run_single_url(
            url="https://example.com",
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            timeout=60,
        )

        assert result.status == RunStatus.SUCCESS
        assert result.csv_row == "CSV,row,data"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_timeout_execution(self, tmp_path):
        """Test timeout d'une URL."""
        mock_crew_class = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance

        async def slow_kickoff(*args, **kwargs):
            await asyncio.sleep(10)
            return MagicMock(raw="data")

        with patch("asyncio.to_thread", side_effect=lambda f, **kw: slow_kickoff()):
            result = await run_single_url(
                url="https://slow.com",
                crew_class=mock_crew_class,
                log_dir=tmp_path,
                timeout=1,
            )

        assert result.status == RunStatus.TIMEOUT
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_exception_execution(self, tmp_path):
        """Test exception durant l'exécution."""
        mock_crew_class = MagicMock()
        mock_crew_class.return_value.crew.return_value.kickoff.side_effect = Exception("API Error")

        result = await run_single_url(
            url="https://error.com",
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            timeout=60,
        )

        assert result.status == RunStatus.FAILED
        assert "API Error" in result.error
```

**Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `pytest tests/shared/utils/test_parallel_runner.py::TestRunSingleUrl -v`
Expected: FAIL avec "cannot import name 'run_single_url'"

**Step 3: Implémenter run_single_url**

```python
# Ajouter à src/wakastart_leads/shared/utils/parallel_runner.py

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any


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
```

**Step 4: Lancer le test pour vérifier qu'il passe**

Run: `pytest tests/shared/utils/test_parallel_runner.py::TestRunSingleUrl -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/wakastart_leads/shared/utils/parallel_runner.py tests/shared/utils/test_parallel_runner.py
git commit -m "feat: add run_single_url async function"
```

---

## Task 5: Implémenter run_parallel avec semaphore

**Files:**
- Modify: `src/wakastart_leads/shared/utils/parallel_runner.py`
- Modify: `tests/shared/utils/test_parallel_runner.py`

**Step 1: Écrire le test pour run_parallel**

```python
# Ajouter à tests/shared/utils/test_parallel_runner.py

from wakastart_leads.shared.utils.parallel_runner import run_parallel


class TestRunParallel:
    @pytest.mark.asyncio
    async def test_parallel_with_semaphore(self, tmp_path):
        """Test limitation du nombre de workers."""
        execution_times = []

        mock_crew_class = MagicMock()

        def create_mock_instance():
            instance = MagicMock()
            instance.crew.return_value.kickoff.return_value = MagicMock(raw="data")
            return instance

        mock_crew_class.side_effect = create_mock_instance

        urls = ["https://a.com", "https://b.com", "https://c.com", "https://d.com"]

        results = await run_parallel(
            urls=urls,
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            max_workers=2,
            timeout=60,
            retry_count=0,
        )

        assert len(results) == 4
        success_count = sum(1 for r in results if r.status == RunStatus.SUCCESS)
        assert success_count == 4

    @pytest.mark.asyncio
    async def test_parallel_one_failure_continues(self, tmp_path):
        """Test que les autres URLs continuent si une échoue."""
        call_count = [0]

        def create_mock_instance():
            call_count[0] += 1
            instance = MagicMock()
            if call_count[0] == 2:
                instance.crew.return_value.kickoff.side_effect = Exception("Error on URL 2")
            else:
                instance.crew.return_value.kickoff.return_value = MagicMock(raw="data")
            return instance

        mock_crew_class = MagicMock(side_effect=create_mock_instance)

        urls = ["https://a.com", "https://b.com", "https://c.com"]

        results = await run_parallel(
            urls=urls,
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            max_workers=1,
            timeout=60,
            retry_count=0,
        )

        assert len(results) == 3
        success_count = sum(1 for r in results if r.status == RunStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == RunStatus.FAILED)
        assert success_count == 2
        assert failed_count == 1
```

**Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `pytest tests/shared/utils/test_parallel_runner.py::TestRunParallel -v`
Expected: FAIL avec "cannot import name 'run_parallel'"

**Step 3: Implémenter run_parallel**

```python
# Ajouter à src/wakastart_leads/shared/utils/parallel_runner.py

async def run_parallel(
    urls: list[str],
    crew_class: Any,
    log_dir: Path,
    max_workers: int = 3,
    timeout: int = 600,
    retry_count: int = 1,
) -> list[UrlResult]:
    """
    Exécute le crew pour plusieurs URLs en parallèle.

    Args:
        urls: Liste des URLs à traiter
        crew_class: Classe du crew à instancier
        log_dir: Dossier pour les logs
        max_workers: Nombre maximum d'exécutions simultanées
        timeout: Timeout par URL en secondes
        retry_count: Nombre de retry en cas d'échec

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
```

**Step 4: Lancer le test pour vérifier qu'il passe**

Run: `pytest tests/shared/utils/test_parallel_runner.py::TestRunParallel -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/wakastart_leads/shared/utils/parallel_runner.py tests/shared/utils/test_parallel_runner.py
git commit -m "feat: add run_parallel with semaphore and retry"
```

---

## Task 6: Implémenter merge_results_to_csv

**Files:**
- Modify: `src/wakastart_leads/shared/utils/parallel_runner.py`
- Modify: `tests/shared/utils/test_parallel_runner.py`

**Step 1: Écrire le test pour merge_results_to_csv**

```python
# Ajouter à tests/shared/utils/test_parallel_runner.py

from wakastart_leads.shared.utils.parallel_runner import merge_results_to_csv


class TestMergeResultsToCsv:
    def test_merge_success_only(self, tmp_path):
        """Fusionne uniquement les résultats réussis."""
        results = [
            UrlResult("https://a.com", RunStatus.SUCCESS, "A,https://a.com,FR", None, 10),
            UrlResult("https://b.com", RunStatus.FAILED, None, "error", 5),
            UrlResult("https://c.com", RunStatus.SUCCESS, "C,https://c.com,US", None, 15),
        ]

        output = tmp_path / "report.csv"
        backup_dir = tmp_path / "backups"

        merge_results_to_csv(results, output, backup_dir)

        assert output.exists()
        content = output.read_text()
        assert "A,https://a.com,FR" in content
        assert "C,https://c.com,US" in content
        assert "error" not in content

    def test_merge_creates_backup(self, tmp_path):
        """Crée un backup si le fichier existe déjà."""
        output = tmp_path / "report.csv"
        backup_dir = tmp_path / "backups"

        # Créer un fichier existant
        output.write_text("OLD,DATA")

        results = [
            UrlResult("https://new.com", RunStatus.SUCCESS, "NEW,DATA", None, 10),
        ]

        merge_results_to_csv(results, output, backup_dir)

        # Vérifier le backup
        assert backup_dir.exists()
        backups = list(backup_dir.glob("*.csv"))
        assert len(backups) == 1
        assert "OLD,DATA" in backups[0].read_text()

        # Vérifier le nouveau contenu
        assert "NEW,DATA" in output.read_text()

    def test_merge_empty_results(self, tmp_path):
        """Gère une liste de résultats vide."""
        results = []
        output = tmp_path / "report.csv"
        backup_dir = tmp_path / "backups"

        merge_results_to_csv(results, output, backup_dir)

        assert output.exists()
        # Fichier avec header uniquement
        content = output.read_text()
        assert "Societe" in content  # Header présent
```

**Step 2: Lancer le test pour vérifier qu'il échoue**

Run: `pytest tests/shared/utils/test_parallel_runner.py::TestMergeResultsToCsv -v`
Expected: FAIL avec "cannot import name 'merge_results_to_csv'"

**Step 3: Implémenter merge_results_to_csv**

```python
# Ajouter à src/wakastart_leads/shared/utils/parallel_runner.py

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
```

**Step 4: Lancer le test pour vérifier qu'il passe**

Run: `pytest tests/shared/utils/test_parallel_runner.py::TestMergeResultsToCsv -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/wakastart_leads/shared/utils/parallel_runner.py tests/shared/utils/test_parallel_runner.py
git commit -m "feat: add merge_results_to_csv function"
```

---

## Task 7: Exporter les fonctions dans __init__.py

**Files:**
- Modify: `src/wakastart_leads/shared/utils/__init__.py`

**Step 1: Lire le fichier actuel**

Vérifier les exports existants.

**Step 2: Ajouter les exports du parallel_runner**

```python
# Ajouter aux imports existants
from .parallel_runner import (
    RunStatus,
    UrlResult,
    run_parallel,
    run_single_url,
    merge_results_to_csv,
)
```

**Step 3: Vérifier l'import**

Run: `python -c "from wakastart_leads.shared.utils import run_parallel, merge_results_to_csv; print('OK')"`
Expected: "OK"

**Step 4: Commit**

```bash
git add src/wakastart_leads/shared/utils/__init__.py
git commit -m "feat: export parallel_runner functions"
```

---

## Task 8: Modifier main.py pour le mode parallèle

**Files:**
- Modify: `src/wakastart_leads/main.py`

**Step 1: Ajouter les imports nécessaires**

```python
# Ajouter en haut du fichier, après les imports existants
import asyncio
```

**Step 2: Modifier la fonction run() pour supporter les arguments CLI**

```python
def run() -> None:
    """Run the analysis crew."""
    import argparse

    parser = argparse.ArgumentParser(description="Run the analysis crew")
    parser.add_argument(
        "--parallel", "-p",
        type=int,
        default=1,
        help="Nombre de workers parallèles (1 = séquentiel)",
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
        help="Nombre de retry par URL en cas d'échec",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout par URL en secondes (défaut: 600)",
    )

    args, _ = parser.parse_known_args(sys.argv[2:] if len(sys.argv) > 2 else [])

    urls = load_urls(ANALYSIS_INPUT)

    if args.batch:
        _run_batch_mode(urls)
    else:
        asyncio.run(_run_parallel_mode(urls, args))
```

**Step 3: Ajouter la fonction _run_batch_mode (ancien comportement)**

```python
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
```

**Step 4: Ajouter la fonction _run_parallel_mode**

```python
async def _run_parallel_mode(urls: list[str], args) -> None:
    """Mode parallèle : chaque URL est traitée indépendamment."""
    from wakastart_leads.shared.utils import run_parallel, merge_results_to_csv

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

    # Fusion des résultats
    merge_results_to_csv(
        results=results,
        output_path=ANALYSIS_OUTPUT / "company_report.csv",
        backup_dir=ANALYSIS_OUTPUT / "backups",
    )

    # Résumé
    success = sum(1 for r in results if r.status.value == "success")
    failed = sum(1 for r in results if r.status.value == "failed")
    timeout = sum(1 for r in results if r.status.value == "timeout")

    print(f"\n{'=' * 50}")
    print(f"[DONE] Résultats:")
    print(f"  - Succès: {success}")
    print(f"  - Échecs: {failed}")
    print(f"  - Timeouts: {timeout}")
    print(f"[OUTPUT] {ANALYSIS_OUTPUT / 'company_report.csv'}")

    cleanup_old_logs(log_dir)
```

**Step 5: Tester la commande help**

Run: `python -m wakastart_leads.main run --help`
Expected: Affiche les options --parallel, --batch, --retry, --timeout

**Step 6: Commit**

```bash
git add src/wakastart_leads/main.py
git commit -m "feat: add parallel mode to run command with CLI flags"
```

---

## Task 9: Mettre à jour le fichier CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Ajouter la documentation des nouvelles options CLI**

Dans la section "Commands", ajouter :

```markdown
# Run the analysis crew (nouveaux modes)
python -m wakastart_leads.main run                    # Mode par défaut (1 URL à la fois)
python -m wakastart_leads.main run --parallel 3      # 3 URLs en parallèle
python -m wakastart_leads.main run --parallel 5 --retry 2 --timeout 900
python -m wakastart_leads.main run --batch           # Mode legacy (ancien comportement)
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add parallel mode documentation to CLAUDE.md"
```

---

## Task 10: Test d'intégration manuel

**Step 1: Préparer le fichier de test avec 2 URLs**

Vérifier que `liste_test.json` contient au moins 2 URLs.

**Step 2: Lancer en mode séquentiel (1 worker)**

Run: `python -m wakastart_leads.main run`
Expected: Les URLs sont traitées une par une, CSV généré.

**Step 3: Lancer en mode parallèle (2 workers)**

Run: `python -m wakastart_leads.main run --parallel 2`
Expected: Les URLs sont traitées en parallèle, CSV généré.

**Step 4: Vérifier le CSV généré**

Run: `head -5 src/wakastart_leads/crews/analysis/output/company_report.csv`
Expected: Header 23 colonnes + lignes de données.

**Step 5: Vérifier les logs individuels**

Run: `ls -la src/wakastart_leads/crews/analysis/output/logs/`
Expected: Un fichier log par URL traitée.

---

## Vérification finale

1. **Tests unitaires complets** : `pytest tests/shared/utils/test_parallel_runner.py -v`
2. **Tous les tests du projet** : `pytest -v`
3. **Test manuel séquentiel** : `python -m wakastart_leads.main run`
4. **Test manuel parallèle** : `python -m wakastart_leads.main run -p 2`
5. **Mode batch legacy** : `python -m wakastart_leads.main run --batch`
