# WakaStart Leads

Systeme multi-agents [CrewAI](https://crewai.com) pour le sourcing et l'enrichissement automatise de leads qualifies pour **WakaStart** (plateforme SaaS de WakaStellar).

## Objectif

Identifier, analyser et scorer des entreprises ayant une composante SaaS (averee ou cachee) pour determiner leur pertinence vis-a-vis des offres WakaStart.

- **Cibles** : StartUp, ScaleUp, Editeurs Legacy avec composante SaaS
- **Geographie** : France (priorite) + International (si lien fort France)
- **Output** : CSV de 23 colonnes avec scoring, strategie commerciale, page Gamma et coordonnees des decideurs

## Installation

Python >=3.10 <3.14 requis. Le projet utilise [UV](https://docs.astral.sh/uv/) pour la gestion des dependances.

```bash
pip install uv
crewai install
```

## Configuration

Creer un fichier `.env` a la racine :

```bash
# APIs LLM (Required)
OPENAI_API_KEY=...          # Required - GPT-4o
ANTHROPIC_API_KEY=...       # Required - Claude Sonnet 4.5

# API Recherche (Required)
SERPER_API_KEY=...          # Required - Recherche web

# APIs Enrichissement (Optional)
PAPPERS_API_KEY=...         # Optional - Donnees legales entreprises
HUNTER_API_KEY=...          # Optional - Decideurs via Hunter.io Domain Search
GAMMA_API_KEY=...           # Optional - Creation pages web via API Gamma

# Linkener - URL Shortener (Optional)
LINKENER_API_BASE=https://url.wakastart.com/api
LINKENER_USERNAME=...       # Optional - Si absent, URLs Gamma brutes utilisees
LINKENER_PASSWORD=...       # Optional
```

## Utilisation

```bash
# Lancer le crew d'analyse
python -m wakastart_leads.main run

# Lancer le crew de recherche d'URLs
python -m wakastart_leads.main search
python -m wakastart_leads.main search --criteria path/to/file.json --output output/urls.json

# Lancer l'enrichissement de donnees
python -m wakastart_leads.main enrich
python -m wakastart_leads.main enrich --test                    # Mode test (20 URLs)
python -m wakastart_leads.main enrich --input path/to/file.csv  # CSV specifique
python -m wakastart_leads.main enrich --batch-size 10           # Taille de batch

# Entrainement et replay
python -m wakastart_leads.main train <n_iterations> <output_filename>
python -m wakastart_leads.main replay <task_id>
python -m wakastart_leads.main test <n_iterations> <model_name>

# Tests unitaires
pytest
pytest -v  # Mode verbose
```

## Architecture

Le projet comporte **3 crews** independants, chacun isole dans son propre dossier avec config, tools, input et output :

```
src/wakastart_leads/
├── main.py                      # Point d'entree CLI
├── crews/
│   ├── analysis/                # Crew 1 : Analyse d'entreprises
│   │   ├── crew.py              # AnalysisCrew (6 agents, 6 taches)
│   │   ├── config/              # agents.yaml, tasks.yaml
│   │   ├── tools/               # gamma_tool.py, hunter_tool.py
│   │   ├── input/               # liste.json, liste_test.json
│   │   └── output/              # company_report.csv, logs/, backups/
│   ├── search/                  # Crew 2 : Recherche d'URLs
│   │   ├── crew.py              # SearchCrew
│   │   ├── config/              # agents.yaml, tasks.yaml
│   │   ├── input/               # search_criteria.json
│   │   └── output/              # search_results_raw.json, logs/
│   └── enrichment/              # Crew 3 : Enrichissement CSV
│       ├── crew.py              # EnrichmentCrew
│       ├── config/              # agents.yaml, tasks.yaml
│       ├── input/               # CSV fourni par l'utilisateur
│       └── output/              # enrichment_accumulated.json, logs/
└── shared/
    ├── tools/                   # pappers_tool.py (partage)
    └── utils/                   # url_utils, csv_utils, log_rotation, constants
```

### Crew 1 : Analyse d'entreprises

```
URLs (JSON) --> ACT 0+1+1bis --> ACT 2+3 --> ACT 4 --> Gamma --> ACT 5 --> Compilation --> CSV (23 cols)
```

| Etape | Agent | Modele LLM | Role |
|-------|-------|------------|------|
| ACT 0+1+1bis | Expert Intelligence Economique | GPT-4o (temp 0.2) | Validation URLs, extraction nom, **extraction SIREN (mentions legales)**, detection SaaS cache |
| ACT 2+3 | Analyste Donnees & Architecte Solutions | GPT-4o (temp 0.4) * | Nationalite, annee creation (via SIREN/Pappers), qualification SaaS |
| ACT 4 | Ingenieur Commercial WakaStart | GPT-4o (temp 0.6) * | Scoring pertinence (0-100%), angle d'attaque commercial |
| Gamma | Architecte Contenu Commercial Digital | GPT-4o (temp 0.3) | Creation page Gamma + raccourcissement URL via Linkener |
| ACT 5 | Expert Lead Generation | GPT-4o (temp 0.2) * | Identification decideurs + enrichissement Hunter.io (email, telephone) |
| Final | Data Compiler | GPT-4o (temp 0.1) | Compilation CSV finale (23 colonnes) |

*\* Note : Ces agents utilisent temporairement GPT-4o au lieu de Claude Sonnet 4.5 (limite API). A rebasculer quand les quotas seront augmentes.*

**Tools specifiques** : `GammaCreateTool` (avec integration Linkener), `HunterDomainSearchTool`

### Crew 2 : Recherche d'URLs

```
Criteres (JSON) --> Decouverte web --> Validation legale --> Scan SaaS --> JSON (URLs)
```

| Phase | Tache | Role |
|-------|-------|------|
| 1 | Decouverte web | Recherche via Serper selon criteres |
| 2 | Validation legale | Verification via Pappers |
| 3 | Scan SaaS | Verification SaaS approfondie + compilation JSON |

- **Agent** : Expert en Veille Strategique & Detection SaaS (`saas_discovery_scout`)
- **Modele** : Claude Sonnet 4.5 (temp 0.3)
- **Input** : `crews/search/input/search_criteria.json`
- **Output** : `crews/search/output/search_results_raw.json`

### Crew 3 : Enrichissement de donnees

```
CSV existant --> Extraction URLs --> Enrichissement batch --> CSV enrichi
```

- **Agent** : Expert en Analyse SaaS (`saas_enrichment_analyst`)
- **Modele** : GPT-4o (temp 0.3)
- **Input** : CSV avec colonne "Site Internet"
- **Output** : CSV enrichi + `crews/enrichment/output/enrichment_accumulated.json`

Colonnes ajoutees :
- **Nationalite** : Emoji drapeau du siege social
- **Solution SaaS** : Secteur + description (max 20 mots)
- **Pertinence** : Score 0-100% selon matrice WakaStart
- **Explication** : Justification avec qualification et module WakaStart recommande

### Tools

| Tool | Emplacement | Description |
|------|-------------|-------------|
| **ScrapeWebsiteTool** | CrewAI built-in | Scraping de contenu web |
| **SerperDevTool** | CrewAI built-in | Recherche Google via API Serper |
| **PappersSearchTool** | `shared/tools/` | Donnees legales entreprises (SIREN, dirigeants, CA) |
| **HunterDomainSearchTool** | `crews/analysis/tools/` | Enrichissement decideurs via Hunter.io Domain Search |
| **GammaCreateTool** | `crews/analysis/tools/` | Creation pages web Gamma + raccourcissement URL Linkener |

#### GammaCreateTool - Workflow

```
Nom entreprise + URL
        │
        ▼
┌───────────────────────┐
│  Recuperation logo    │ ← Unavatar / Google Favicon
│  (Unavatar/Favicon)   │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Redimensionnement    │ ← wsrv.nl (150×80px, gratuit)
│  via proxy wsrv.nl    │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Creation page Gamma  │ ← API Gamma + prompt optimise
│  (avec logos alignes) │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Raccourcissement URL │ ← Linkener (optionnel)
│  (si configure)       │
└───────────────────────┘
        │
        ▼
URL finale (courte ou brute)
```

#### GammaCreateTool - Fonctionnalites

Le `GammaCreateTool` integre desormais :

1. **Redimensionnement automatique des logos via proxy** :
   - Utilise [wsrv.nl](https://wsrv.nl) (service gratuit, sans cle API)
   - Redimensionne tous les logos a 150×80 px (`fit=contain`, preserve les proportions)
   - Applique aux logos Unavatar et Google Favicon avant injection dans le prompt
   - Garantit une apparence professionnelle et coherente sur la title card

2. **Instructions de dimensionnement Gamma** :
   - Prompt explicite pour que les 3 logos (entreprise, Opportunity Analysis, WakaStellar) soient alignes horizontalement
   - Cible de hauteur 60-80px pour une harmonie visuelle

3. **Integration Linkener** (optionnel) : Raccourcissement automatique des URLs Gamma
   - Convertit les noms d'entreprise en slugs URL-safe (`France-Care` → `france-care`)
   - Genere des URLs courtes : `https://url.wakastart.com/france-care`
   - Gestion des collisions (ajout de suffixe numerique si slug deja pris)
   - Fallback automatique vers l'URL Gamma brute si Linkener non configure

#### HunterDomainSearchTool - Fonctionnalites

Le `HunterDomainSearchTool` recherche les decideurs d'une entreprise via l'API Hunter.io :

```
Domaine entreprise (ex: stripe.com)
        │
        ▼
┌───────────────────────┐
│  API Hunter.io        │ ← Domain Search endpoint
│  (1 seul appel)       │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Tri par seniority    │ ← executive > senior > autres
│  puis par confidence  │
└───────────────────────┘
        │
        ▼
3 decideurs avec coordonnees
(nom, titre, email, telephone, LinkedIn)
```

**Avantages par rapport a Kaspr** :
- **1 appel API au lieu de 3** : Hunter retourne directement les decideurs
- **Moins de dependance au scraping** : Pas besoin de chercher les profils LinkedIn
- **Filtrage automatique** : Exclut les emails generiques (contact@, info@)
- **Tri intelligent** : Priorite aux C-Level (executive) puis Management (senior)

### Services externes

| Service | Type | Usage | Cle API |
|---------|------|-------|---------|
| **Hunter.io** | Enrichissement | Decideurs C-Level/Management (email, telephone) | Optionnel (via .env) |
| **wsrv.nl** | Proxy images | Redimensionnement logos (150×80px) | Non requise (gratuit) |
| **Unavatar** | Logos | Recuperation logos entreprises | Non requise |
| **Linkener** | URL Shortener | URLs courtes brandees | Optionnel (via .env) |

## Output CSV

Fichier : `crews/analysis/output/company_report.csv` (UTF-8 BOM pour Excel)

23 colonnes par entreprise :
- **Entreprise** : Nom, Site Web, Nationalite, Annee Creation
- **SaaS** : Description solution (max 20 mots)
- **Scoring** : Pertinence (0-100%), Strategie & Angle d'attaque commercial
- **Decideurs** (x3) : Nom, Titre, Email, Telephone, LinkedIn
- **Page Gamma** : URL courte Linkener (`https://url.wakastart.com/nom-entreprise`) ou URL Gamma brute si Linkener non configure

## Scoring WakaStart

| Score | Profil type |
|-------|-------------|
| 90-100% | Sante (besoin HDS) + stack vieillissante |
| 80-90% | Finance/B2B grands comptes + besoin ISO 27001/NIS2 |
| 70-80% | Levee de fonds recente + besoin acceleration dev |
| 60-70% | Stack PHP/Python legacy + pas d'evolution 5+ ans |
| 50-60% | SaaS B2B avec besoin multi-tenant/marque blanche |
| <50% | Pas de SaaS clair ou pas d'ancrage France |

## Logging

Chaque crew genere ses logs dans son propre dossier `output/logs/` :
- `crews/analysis/output/logs/run_YYYYMMDD_HHMMSS.json`
- `crews/search/output/logs/search_YYYYMMDD_HHMMSS.json`
- `crews/enrichment/output/logs/enrich_YYYYMMDD_HHMMSS.json`

**Rotation automatique** : Les logs > 30 jours sont supprimes automatiquement.

## Tests

222 tests unitaires avec pytest couvrant les 3 crews, les 4 tools custom et les utilitaires.

Tests pour `HunterDomainSearchTool` (27 tests) :
- `TestBuildLinkedinUrl` (5 tests) - Construction URLs LinkedIn
- `TestSortContacts` (5 tests) - Tri par seniority puis confidence
- `TestFormatDecideurs` (5 tests) - Formatage structure decideurs
- `TestHunterRun` (10 tests) - Appels API et gestion erreurs

Tests pour `GammaCreateTool` (56 tests) :
- `TestSanitizeSlug` (7 tests) - Conversion noms → slugs URL-safe
- `TestGetLinkenerToken` (4 tests) - Authentification Linkener
- `TestCreateLinkenerUrl` (5 tests) - Creation URLs courtes + gestion collisions

```bash
pytest                           # Tous les tests
pytest tests/crews/analysis/     # Tests crew Analysis
pytest tests/shared/tools/       # Tests tools partages
pytest -v                        # Mode verbose
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
- Documentation API dans les dossiers tools concernés
