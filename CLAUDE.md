# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## References importantes

- @README.md - Apercu du projet
- @pyproject.toml - Configuration Python et dependances

### Documentation API (NE PAS CHARGER automatiquement)

Pour Pappers, utiliser le resume condense (2k chars) :
- @src/wakastart_leads/shared/tools/pappers_api_summary.md

Fichiers complets (lire avec Read tool uniquement si besoin de details) :
- Pappers complet (336k chars): `src/wakastart_leads/shared/tools/pappers_api.yaml`
- Hunter.io: `docs/hunter_io_api.txt`
- Gamma: `src/wakastart_leads/crews/analysis/tools/gamma_api.txt`

### Configuration des agents (NE PAS CHARGER - lire manuellement si besoin)

Ces fichiers de config sont charges uniquement si on travaille sur les agents :
- Analysis agents: `src/wakastart_leads/crews/analysis/config/agents.yaml`
- Analysis tasks: `src/wakastart_leads/crews/analysis/config/tasks.yaml`
- Search config: `src/wakastart_leads/crews/search/config/agents.yaml`
- Enrichment config: `src/wakastart_leads/crews/enrichment/config/agents.yaml`

## Project Overview

**WakaStart Leads** - Systeme multi-agents CrewAI pour le sourcing et l'enrichissement de leads qualifies pour **WakaStart** (plateforme SaaS de WakaStellar).

**Objectif** : Identifier, analyser et scorer des entreprises ayant une composante SaaS (averee ou cachee) pour determiner leur pertinence vis-a-vis des offres WakaStart.

**Cibles** : StartUp, ScaleUp, Legacy avec composante SaaS
**Geographie** : France (priorite) + International (si lien fort France)

## Commands

```bash
# Install dependencies (creates .venv with Python 3.10)
crewai install

# Run the crew (mode parallele par defaut)
python -m wakastart_leads.main run                    # Mode par defaut (1 URL a la fois)
python -m wakastart_leads.main run --parallel 3      # 3 URLs en parallele
python -m wakastart_leads.main run --parallel 5 --retry 2 --timeout 900
python -m wakastart_leads.main run --batch           # Mode legacy (ancien comportement)

# Search for SaaS URLs
python -m wakastart_leads.main search
python -m wakastart_leads.main search --criteria path/to/file.json --output output/urls.json

# Enrich company CSV
python -m wakastart_leads.main enrich
python -m wakastart_leads.main enrich --test
python -m wakastart_leads.main enrich --input path/to/file.csv --output path/to/output.csv
python -m wakastart_leads.main enrich --batch-size 10

# Train/Test/Replay
python -m wakastart_leads.main train N FILE
python -m wakastart_leads.main replay TASKID
python -m wakastart_leads.main test N MODEL

# Add new dependencies
uv add <package-name>

# Run unit tests
pytest
```

## Architecture

Le projet comporte **3 crews** independants, chacun isole dans son propre dossier :

```
src/wakastart_leads/
├── main.py                      # Point d'entree CLI
├── crews/
│   ├── analysis/                # Crew 1 : Analyse d'entreprises
│   │   ├── crew.py              # AnalysisCrew
│   │   ├── config/              # agents.yaml, tasks.yaml
│   │   ├── tools/               # gamma_tool.py, hunter_tool.py + docs API
│   │   ├── input/               # liste.json, liste_test.json
│   │   └── output/              # company_report.csv, logs/, backups/
│   ├── search/                  # Crew 2 : Recherche d'URLs
│   │   ├── crew.py              # SearchCrew
│   │   ├── config/
│   │   ├── input/               # search_criteria.json
│   │   └── output/              # logs/
│   └── enrichment/              # Crew 3 : Enrichissement
│       ├── crew.py              # EnrichmentCrew
│       ├── config/
│       ├── input/               # CSV fourni par l'utilisateur
│       └── output/              # enrichment_accumulated.json, logs/
└── shared/
    ├── tools/                   # pappers_tool.py + doc API
    └── utils/                   # url_utils.py, csv_utils.py, log_rotation.py, constants.py
```

### Crew 1 : Analysis (`src/wakastart_leads/crews/analysis/`)

| ACT | Agent | Modele LLM | Role |
|-----|-------|------------|------|
| 0+1+1bis | `economic_intelligence_analyst` | `openai/gpt-4o` (temp 0.2) | Validation URLs, extraction nom, **extraction SIREN (mentions legales)**, detection SaaS cache |
| 2+3 | `corporate_analyst_and_saas_qualifier` | `openai/gpt-4o` (temp 0.4) ** | Nationalite, annee creation (via SIREN), qualification technique SaaS |
| 4 | `wakastart_sales_engineer` | `openai/gpt-4o` (temp 0.6) ** | Scoring pertinence (0-100%), angle d'attaque commercial |
| Gamma | `gamma_webpage_creator` | `openai/gpt-4o` (temp 0.3) | Creation page Gamma + raccourcissement URL Linkener |
| 5 | `lead_generation_expert` | `openai/gpt-4o` (temp 0.2) ** | Identification des 3 decideurs + enrichissement Hunter.io |
| Final | `data_compiler_and_reporter` | `openai/gpt-4o` (temp 0.1) | Compilation CSV finale (23 colonnes) |

**\*\* Note temporaire** : Ces 3 agents utilisent GPT-4o au lieu de `anthropic/claude-sonnet-4-5-20250929` (limite API atteinte). Rebasculer vers Claude quand les quotas seront augmentes.

**Tools specifiques** : `gamma_tool.py` (avec Linkener), `hunter_tool.py` (dans `crews/analysis/tools/`)

### Crew 2 : Search (`src/wakastart_leads/crews/search/`)

| Phase | Tache | Role |
|-------|-------|------|
| 1 | `search_web_discovery` | Decouverte web via Serper |
| 2 | `search_pappers_validation` | Validation legale via Pappers |
| 3 | `search_saas_deep_scan` | Verification SaaS approfondie + compilation JSON |

- **Agent** : `saas_discovery_scout`
- **Modele** : `anthropic/claude-sonnet-4-5-20250929` (temp 0.3)
- **Output** : `crews/search/output/search_results_raw.json`
- **Input** : `crews/search/input/search_criteria.json`

### Crew 3 : Enrichment (`src/wakastart_leads/crews/enrichment/`)

- **Agent** : `saas_enrichment_analyst`
- **Modele** : `openai/gpt-4o` (temp 0.3)
- **Input** : CSV avec colonne "Site Internet" (fourni par l'utilisateur)
- **Output** : `crews/enrichment/output/enrichment_accumulated.json`

### Shared (`src/wakastart_leads/shared/`)

**Tools partages** (`shared/tools/`) :
- `pappers_tool.py` - Donnees legales via API Pappers (utilise par Analysis + Search)

**Utils** (`shared/utils/`) :
- `url_utils.py` : `normalize_url()`, `load_urls()`, `ensure_https()`
- `csv_utils.py` : `load_existing_csv()`, `post_process_csv()`, `clean_markdown_artifacts()`
- `log_rotation.py` : `cleanup_old_logs()`, `get_log_retention_days()`
- `constants.py` : Chemins et configuration (`ANALYSIS_INPUT`, `ANALYSIS_OUTPUT`, etc.)

### Key Files

| Fichier | Description |
|---------|-------------|
| `src/wakastart_leads/main.py` | Point d'entree CLI (run, search, enrich, train, replay, test) |
| `src/wakastart_leads/crews/analysis/crew.py` | AnalysisCrew (6 agents, 6 taches) |
| `src/wakastart_leads/crews/search/crew.py` | SearchCrew (1 agent, 3 taches) |
| `src/wakastart_leads/crews/enrichment/crew.py` | EnrichmentCrew (1 agent, 1 tache) |
| `src/wakastart_leads/shared/tools/pappers_tool.py` | PappersSearchTool |
| `src/wakastart_leads/crews/analysis/tools/gamma_tool.py` | GammaCreateTool (avec Linkener) |
| `src/wakastart_leads/crews/analysis/tools/hunter_tool.py` | HunterDomainSearchTool |

### GammaCreateTool - Methodes internes

Le `GammaCreateTool` integre plusieurs fonctionnalites :

| Methode | Description |
|---------|-------------|
| `_resize_logo_via_proxy(logo_url)` | Redimensionne un logo via wsrv.nl (150×80px, `fit=contain`) |
| `_resolve_company_logo(name, url)` | Recupere le logo via Unavatar/Favicon + redimensionnement automatique |
| `_build_enhanced_prompt()` | Construit le prompt Gamma avec instructions de dimensionnement logos (60-80px) |
| `_sanitize_slug(name)` | Convertit un nom d'entreprise en slug URL-safe (`France-Care` → `france-care`) |
| `_get_linkener_token(api_base, username, password)` | Authentification API Linkener, retourne un token JWT |
| `_create_linkener_url(gamma_url, company_name)` | Cree une URL courte Linkener, gere les collisions (409) avec suffixe |
| `_run(company_name, ...)` | Workflow complet : logo → Gamma → Linkener (optionnel) |

**Constantes de configuration** :
```python
IMAGE_PROXY_BASE = "https://wsrv.nl"  # Service gratuit, sans cle API
LOGO_TARGET_WIDTH = 150
LOGO_TARGET_HEIGHT = 80
```

**Fallback** : Si Linkener n'est pas configure (variables env absentes), l'URL Gamma brute est retournee.

### Services externes utilises

| Service | URL | Usage | Cle API |
|---------|-----|-------|---------|
| **wsrv.nl** | `https://wsrv.nl` | Proxy de redimensionnement images | Non (gratuit) |
| **Unavatar** | `https://unavatar.io` | Recuperation logos entreprises | Non (gratuit) |
| **Linkener** | `https://url.wakastart.com/api` | Raccourcissement URLs | Optionnel |
| **Hunter.io** | `https://api.hunter.io/v2` | Enrichissement decideurs (email, telephone) | Requis |
| **Zeliq** | `https://api.zeliq.com/api` | Enrichissement email via LinkedIn | Optionnel |

### HunterDomainSearchTool - Methodes internes

Le `HunterDomainSearchTool` recherche les decideurs d'une entreprise via l'API Hunter.io Domain Search :

| Methode | Description |
|---------|-------------|
| `_build_linkedin_url(handle)` | Construit l'URL LinkedIn complete a partir d'un handle |
| `_sort_contacts(contacts)` | Trie par seniority (executive > senior) puis par confidence |
| `_format_decideurs(contacts, company_name)` | Formate les contacts en structure decideurs (3 max) |
| `_run(domain, company_name)` | Appel API Hunter + tri + formatage |

**Parametres API Hunter** :
- `type=personal` : Exclut les emails generiques (contact@, info@)
- `seniority=executive,senior` : Cible C-Level et Management
- `department=executive,management,it` : Departements decisionnaires
- `limit=10` : Marge pour avoir du choix apres tri

**Format de sortie** :
```python
{
    "company": "Stripe",
    "decideurs": [
        {"nom": "Patrick Collison", "titre": "CEO", "email": "...", "telephone": "...", "linkedin": "..."},
        # ... jusqu'a 3 decideurs
    ],
    "contacts_found": 2
}
```

### ZeliqEmailEnrichTool - Methodes internes

Le `ZeliqEmailEnrichTool` enrichit les emails des decideurs via l'API Zeliq :

| Methode | Description |
|---------|-------------|
| `_create_webhook_url()` | Cree une URL unique via webhook.site |
| `_call_zeliq_api(...)` | Appel POST a /contact/enrich/email |
| `_poll_webhook(token_uuid)` | Poll webhook.site jusqu'a reponse (max 30s) |
| `_run(first_name, ...)` | Workflow complet : webhook → API → poll → email |

**Flux d'enrichissement** :
```
LinkedIn URL (Hunter) → Zeliq API → webhook.site → Email enrichi
```

**Regle de priorite** : L'email Zeliq remplace l'email Hunter (plus fiable).
Si Zeliq echoue, l'email Hunter est conserve en fallback.

### Input Format

**Crew d'analyse** : Fichiers dans `crews/analysis/input/`
- `liste_test.json` - URLs pour les tests
- `liste.json` - URLs en production

**Crew de recherche** : `crews/search/input/search_criteria.json`
```json
{
  "keywords": ["SaaS sante", "CRM medical", "healthtech France"],
  "sector": "sante",
  "geographic_zone": "France",
  "company_size": "startup",
  "creation_year_min": 2018,
  "max_results": 30
}
```

**Crew d'enrichissement** : CSV dans `crews/enrichment/input/` avec colonne "Site Internet"

## Output

### Analysis Output (`crews/analysis/output/`)

Fichier : `company_report.csv` (23 colonnes, UTF-8 BOM)

| Col | Nom | Description |
|-----|-----|-------------|
| A | Societe | Nom commercial |
| B | Site Web | URL racine |
| C | Nationalite | FR, INT, US, UK, etc. |
| D | Annee Creation | YYYY |
| E | Solution SaaS | Description courte (max 20 mots) |
| F | Pertinence (%) | Score 0-100 |
| G | Strategie & Angle | Angle commercial WakaStart |
| H-L | Decideur 1 | Nom, Titre, Email, Telephone, LinkedIn |
| M-Q | Decideur 2 | Idem |
| R-V | Decideur 3 | Idem |
| W | Page Gamma | URL courte Linkener ou URL Gamma brute |

### Logging

Chaque crew genere ses logs dans son propre dossier :
- `crews/analysis/output/logs/run_YYYYMMDD_HHMMSS.json`
- `crews/search/output/logs/search_YYYYMMDD_HHMMSS.json`
- `crews/enrichment/output/logs/enrich_YYYYMMDD_HHMMSS.json`

**Rotation automatique** : Les logs > 30 jours sont supprimes (configurable via `LOG_RETENTION_DAYS`)

## Environment

Requires `.env` file with:
```bash
# APIs LLM (Required)
OPENAI_API_KEY=...          # Required - GPT-4o
ANTHROPIC_API_KEY=...       # Required - Claude Sonnet 4.5

# API Recherche (Required)
SERPER_API_KEY=...          # Required - Recherche Google

# APIs Enrichissement (Optional)
PAPPERS_API_KEY=...         # Optional - Donnees legales
HUNTER_API_KEY=...          # Optional - Decideurs via Hunter.io Domain Search
GAMMA_API_KEY=...           # Optional - Pages web Gamma

# Linkener - URL Shortener (Optional)
LINKENER_API_BASE=https://url.wakastart.com/api
LINKENER_USERNAME=...       # Si absent, URLs Gamma brutes
LINKENER_PASSWORD=...
```

## Tests

```bash
pytest                                    # Tous les tests
pytest tests/crews/analysis/              # Tests crew Analysis
pytest tests/shared/tools/                # Tests tools partages
pytest -v                                 # Mode verbose
```

Structure des tests :
```
tests/
├── conftest.py
├── crews/
│   ├── analysis/
│   │   ├── test_crew.py
│   │   └── tools/
│   │       ├── test_gamma_tool.py
│   │       └── test_hunter_tool.py
│   ├── search/
│   │   └── test_crew.py
│   └── enrichment/
└── shared/
    ├── tools/
    │   └── test_pappers_tool.py
    └── utils/
        ├── test_url.py
        ├── test_csv.py
        └── test_search.py
```

## Documentation

- `docs/plans/` - Plans de design et d'implementation
- `docs/business/` - PDFs metier (Projet WakaStart, Protocole)
- `docs/guides/` - Guides (agent-commercial.md)
- Documentation API : `gamma_api.txt`, `pappers_api.yaml`, `docs/hunter_io_api.txt`
