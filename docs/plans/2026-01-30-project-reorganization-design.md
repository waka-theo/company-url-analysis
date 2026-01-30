# Design : Réorganisation du projet WakaStart Leads

**Date** : 2026-01-30
**Statut** : Validé
**Objectifs** : Navigation simplifiée, noms explicites, séparation input/output

---

## Structure cible

```
wakastart_leads/
├── src/wakastart_leads/
│   ├── __init__.py
│   ├── main.py                          # Point d'entrée CLI
│   ├── crews/
│   │   ├── __init__.py
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── crew.py                  # AnalysisCrew
│   │   │   ├── config/
│   │   │   │   ├── agents.yaml
│   │   │   │   └── tasks.yaml
│   │   │   ├── tools/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── gamma_tool.py
│   │   │   │   ├── gamma_api.txt
│   │   │   │   ├── kaspr_tool.py
│   │   │   │   └── kaspr_api.txt
│   │   │   ├── input/
│   │   │   │   ├── liste.json
│   │   │   │   └── liste_test.json
│   │   │   └── output/
│   │   │       ├── company_report.csv
│   │   │       ├── logs/
│   │   │       └── backups/
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── crew.py                  # SearchCrew
│   │   │   ├── config/
│   │   │   │   ├── agents.yaml
│   │   │   │   └── tasks.yaml
│   │   │   ├── input/
│   │   │   │   └── search_criteria.json
│   │   │   └── output/
│   │   │       └── logs/
│   │   └── enrichment/
│   │       ├── __init__.py
│   │       ├── crew.py                  # EnrichmentCrew
│   │       ├── config/
│   │       │   ├── agents.yaml
│   │       │   └── tasks.yaml
│   │       ├── input/
│   │       │   └── .gitkeep             # CSV fourni par l'utilisateur
│   │       └── output/
│   │           ├── enrichment_accumulated.json
│   │           ├── logs/
│   │           └── backups/
│   └── shared/
│       ├── __init__.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── pappers_tool.py
│       │   └── pappers_api.yaml
│       └── utils/
│           ├── __init__.py
│           ├── url_utils.py             # normalize_url(), load_urls()
│           ├── csv_utils.py             # load_existing_csv(), post_process_csv()
│           ├── log_rotation.py          # cleanup_old_logs()
│           └── constants.py             # Chemins, configs communes
├── tests/
│   ├── conftest.py
│   ├── __init__.py
│   ├── crews/
│   │   ├── __init__.py
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── test_crew.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── test_gamma_tool.py
│   │   │       └── test_kaspr_tool.py
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   └── test_crew.py
│   │   └── enrichment/
│   │       ├── __init__.py
│   │       └── test_crew.py
│   ├── shared/
│   │   ├── __init__.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       └── test_pappers_tool.py
│   └── integration/
│       ├── __init__.py
│       └── test_gamma_integration.py
├── docs/
│   ├── plans/                           # Documents de design
│   ├── business/
│   │   ├── Projet WakaStart.pdf
│   │   └── Protocole Théo.pdf
│   └── guides/
│       └── agent-commercial.md
├── public/
│   ├── Logos-Wakstellar_Nom-full-blanc.png
│   └── Gemini_Generated_Image_rzqb15rzqb15rzqb.png
├── knowledge/
│   └── user_preference.txt
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── .env
└── .gitignore
```

---

## Décisions de design

### 1. Organisation par crew isolé

Chaque crew est **auto-contenu** avec :
- Son code (`crew.py`)
- Sa config (`config/agents.yaml`, `config/tasks.yaml`)
- Ses tools spécifiques (`tools/`)
- Ses données (`input/`, `output/`)

**Avantage** : Navigation intuitive, un seul endroit pour tout ce qui concerne un workflow.

### 2. Tools partagés dans shared/

Les tools utilisés par plusieurs crews sont centralisés :

| Tool | Emplacement | Utilisé par |
|------|-------------|-------------|
| `pappers_tool.py` | `shared/tools/` | Analysis, Search |
| `gamma_tool.py` | `crews/analysis/tools/` | Analysis uniquement |
| `kaspr_tool.py` | `crews/analysis/tools/` | Analysis uniquement |

Les tools natifs CrewAI (SerperDevTool, ScrapeWebsiteTool) restent importés directement.

### 3. Documentation API à côté du code

Les fichiers de documentation API sont placés **à côté du tool** qu'ils documentent :
- `gamma_api.txt` → `crews/analysis/tools/`
- `kaspr_api.txt` → `crews/analysis/tools/`
- `pappers_api.yaml` → `shared/tools/`

**Avantage** : Maintenance facilitée, tout le contexte au même endroit.

### 4. Utils extraits de main.py

Les fonctions utilitaires actuellement dans `main.py` sont extraites dans `shared/utils/` :

| Fichier | Fonctions |
|---------|-----------|
| `url_utils.py` | `normalize_url()`, `load_urls()` |
| `csv_utils.py` | `load_existing_csv()`, `post_process_csv()`, `merge_csv()` |
| `log_rotation.py` | `cleanup_old_logs()` |
| `constants.py` | Chemins par défaut, configuration commune |

### 5. Rotation automatique des logs

```python
# shared/utils/log_rotation.py

import os
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_logs(
    logs_dir: Path,
    max_age_days: int = 30,
    min_keep: int = 5
) -> int:
    """
    Supprime les fichiers de logs plus vieux que max_age_days.
    Garde toujours au minimum min_keep fichiers.

    Returns:
        Nombre de fichiers supprimés
    """
    ...
```

- Appelée à la fin de chaque run de crew
- Configurable via `LOG_RETENTION_DAYS` (défaut : 30)
- Garde minimum 5 fichiers même si > 30 jours

---

## Mapping des fichiers (ancien → nouveau)

| Ancien chemin | Nouveau chemin |
|---------------|----------------|
| `src/company_url_analysis_automation/` | `src/wakastart_leads/` |
| `src/.../crew.py` | `src/.../crews/analysis/crew.py` |
| `src/.../search_crew.py` | `src/.../crews/search/crew.py` |
| `src/.../enrichment_crew.py` | `src/.../crews/enrichment/crew.py` |
| `src/.../config/agents.yaml` | `src/.../crews/analysis/config/agents.yaml` |
| `src/.../config/search_agents.yaml` | `src/.../crews/search/config/agents.yaml` |
| `src/.../config/enrichment_agents.yaml` | `src/.../crews/enrichment/config/agents.yaml` |
| `src/.../config/tasks.yaml` | `src/.../crews/analysis/config/tasks.yaml` |
| `src/.../config/search_tasks.yaml` | `src/.../crews/search/config/tasks.yaml` |
| `src/.../config/enrichment_tasks.yaml` | `src/.../crews/enrichment/config/tasks.yaml` |
| `src/.../tools/gamma_tool.py` | `src/.../crews/analysis/tools/gamma_tool.py` |
| `src/.../tools/kaspr_tool.py` | `src/.../crews/analysis/tools/kaspr_tool.py` |
| `src/.../tools/pappers_tool.py` | `src/.../shared/tools/pappers_tool.py` |
| `liste.json` | `src/.../crews/analysis/input/liste.json` |
| `liste_test.json` | `src/.../crews/analysis/input/liste_test.json` |
| `search_criteria.json` | `src/.../crews/search/input/search_criteria.json` |
| `output/company_report.csv` | `src/.../crews/analysis/output/company_report.csv` |
| `output/logs/enrich/` | `src/.../crews/enrichment/output/logs/` |
| `output/backups/` | `src/.../crews/analysis/output/backups/` |
| `docs/kaspr.txt` | `src/.../crews/analysis/tools/kaspr_api.txt` |
| `docs/gamma_api.txt` | `src/.../crews/analysis/tools/gamma_api.txt` |
| `docs/pappers_api_v2.yaml` | `src/.../shared/tools/pappers_api.yaml` |
| `docs/Projet WakaStart.pdf` | `docs/business/Projet WakaStart.pdf` |
| `docs/Protocole Théo.pdf` | `docs/business/Protocole Théo.pdf` |
| `docs/agent-commercial.md` | `docs/guides/agent-commercial.md` |
| `tests/test_main.py` | `tests/crews/analysis/test_crew.py` (+ shared) |
| `tests/tools/test_gamma_tool.py` | `tests/crews/analysis/tools/test_gamma_tool.py` |
| `tests/tools/test_pappers_tool.py` | `tests/shared/tools/test_pappers_tool.py` |

---

## Modifications pyproject.toml

```toml
[project]
name = "wakastart_leads"
version = "0.1.0"
description = "Multi-agent system for SaaS lead sourcing and enrichment"

[project.scripts]
wakastart = "wakastart_leads.main:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

---

## Nouveaux imports

```python
# Crews
from wakastart_leads.crews.analysis import AnalysisCrew
from wakastart_leads.crews.search import SearchCrew
from wakastart_leads.crews.enrichment import EnrichmentCrew

# Tools spécifiques
from wakastart_leads.crews.analysis.tools.gamma_tool import GammaCreateTool
from wakastart_leads.crews.analysis.tools.kaspr_tool import KasprEnrichTool

# Tools partagés
from wakastart_leads.shared.tools.pappers_tool import PappersSearchTool

# Utils
from wakastart_leads.shared.utils.url_utils import normalize_url, load_urls
from wakastart_leads.shared.utils.csv_utils import load_existing_csv, post_process_csv
from wakastart_leads.shared.utils.log_rotation import cleanup_old_logs
```

---

## Commandes CLI (inchangées)

```bash
python main.py run              # Lance AnalysisCrew
python main.py search           # Lance SearchCrew
python main.py enrich           # Lance EnrichmentCrew
python main.py enrich --test    # Mode test (20 URLs)
```

---

## Plan d'implémentation

### Phase 1 : Création de la structure
1. Créer l'arborescence de dossiers
2. Déplacer les fichiers existants
3. Créer les `__init__.py`

### Phase 2 : Refactoring du code
4. Extraire les utils de `main.py` vers `shared/utils/`
5. Mettre à jour les imports dans tous les fichiers
6. Adapter les chemins dans les crews (config, input, output)

### Phase 3 : Tests et validation
7. Mettre à jour la structure des tests
8. Corriger les imports dans les tests
9. Vérifier que `pytest` passe

### Phase 4 : Configuration
10. Mettre à jour `pyproject.toml`
11. Mettre à jour `CLAUDE.md`
12. Mettre à jour `README.md`

### Phase 5 : Nettoyage
13. Supprimer les anciens fichiers/dossiers vides
14. Implémenter la rotation des logs
15. Commit final

---

## Fichiers à supprimer après migration

- `src/company_url_analysis_automation/` (ancien package)
- `output/` à la racine (déplacé dans les crews)
- `liste.json`, `liste_test.json`, `search_criteria.json` à la racine
- `docs/kaspr.txt`, `docs/gamma_api.txt`, `docs/pappers_api_v2.yaml`
- `docs/linkener-*.txt` (si non utilisés)
