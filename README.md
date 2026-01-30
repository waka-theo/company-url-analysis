# Protocole AUTO MASS PROJECT

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
OPENAI_API_KEY=...          # Required - GPT-4o
ANTHROPIC_API_KEY=...       # Required - Claude Sonnet 4.5
SERPER_API_KEY=...          # Required - Recherche web
PAPPERS_API_KEY=...         # Optional - Donnees legales entreprises
KASPR_API_KEY=...           # Optional - Enrichissement contacts (email + telephone)
GAMMA_API_KEY=...           # Optional - Creation pages web via API Gamma
```

## Utilisation

```bash
# Lancer le crew d'analyse (mode test avec liste_test.json)
crewai run

# Lancer le crew de recherche d'URLs
python main.py search
python main.py search --criteria path/to/file.json --output output/urls.json

# Lancer l'enrichissement de donnees
python main.py enrich
python main.py enrich --test
python main.py enrich --input path/to/file.csv --batch-size 10

# Entrainement
crewai train <n_iterations> <output_filename>

# Replay d'une tache specifique
crewai replay <task_id>
```

## Architecture

Le projet comporte **3 crews** independants.

### Crew 1 : Analyse d'entreprises (6 taches sequentielles)

```
URLs (JSON) --> ACT 0+1 --> ACT 2+3 --> ACT 4 --> Gamma --> ACT 5 --> Compilation --> CSV (23 cols)
```

| Etape | Agent | Modele LLM | Role |
|-------|-------|------------|------|
| ACT 0+1 | Expert Intelligence Economique | GPT-4o (temp 0.2) | Validation URLs, extraction nom, detection SaaS cache |
| ACT 2+3 | Analyste Donnees & Architecte Solutions | Claude Sonnet 4.5 (temp 0.4) | Nationalite, annee creation, qualification SaaS |
| ACT 4 | Ingenieur Commercial WakaStart | Claude Sonnet 4.5 (temp 0.6) | Scoring pertinence (0-100%), angle d'attaque commercial |
| Gamma | Architecte Contenu Commercial Digital | GPT-4o (temp 0.3) | Creation page web Gamma avec logos dynamiques |
| ACT 5 | Expert Lead Generation | Claude Sonnet 4.5 (temp 0.2) | Identification decideurs + enrichissement Kaspr (email, telephone) |
| Final | Data Compiler | GPT-4o (temp 0.1) | Compilation CSV finale (23 colonnes) |

### Crew 2 : Recherche d'URLs (`SearchCrew`)

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
- **Input** : `search_criteria.json`
- **Output** : `output/search_results_raw.json`

### Crew 3 : Enrichissement de donnees (`EnrichmentCrew`)

```
CSV existant --> Extraction URLs --> Enrichissement batch --> CSV enrichi
```

- **Agent** : Expert en Analyse SaaS (`saas_enrichment_analyst`)
- **Modele** : GPT-4o (temp 0.3)
- **Input** : CSV avec colonne "Site Internet"
- **Output** : CSV enrichi + `output/enrichment_accumulated.json`

Colonnes ajoutees :
- Nationalite (emoji drapeau)
- Solution SaaS (secteur + description max 20 mots)
- Pertinence (score 0-100%)
- Explication (justification WakaStart)

### Tools

- **ScrapeWebsiteTool** : Scraping de contenu web
- **SerperDevTool** : Recherche Google via API Serper
- **PappersSearchTool** : Donnees legales entreprises (SIREN, dirigeants, CA)
- **KasprEnrichTool** : Enrichissement contacts via LinkedIn (email pro, telephone)
- **GammaCreateTool** : Creation pages web via API Gamma (template + logos dynamiques Clearbit/Google)

### Fichiers principaux

```
src/company_url_analysis_automation/
  crew.py              # Definitions agents, taches, crew d'analyse
  search_crew.py       # Definitions du crew de recherche (SearchCrew)
  enrichment_crew.py   # Definitions du crew d'enrichissement (EnrichmentCrew)
  main.py              # Entry point + post-processing CSV et JSON
  config/
    agents.yaml        # Roles et backstories des 7 agents
    tasks.yaml         # Descriptions des 9 taches
    enrichment_agents.yaml  # Agent saas_enrichment_analyst
    enrichment_tasks.yaml   # Tache + matrice de scoring WakaStart
  tools/
    __init__.py
    kaspr_tool.py      # API Kaspr (enrichissement contacts)
    pappers_tool.py    # API Pappers (donnees legales)
    gamma_tool.py      # API Gamma (creation pages web + logos)
tests/
  conftest.py            # Fixtures partagees et mocks API
  test_main.py           # Tests crew d'analyse (load_urls, post_process_csv)
  test_search_crew.py    # Tests SearchCrew (agent, taches, config)
  test_search_main.py    # Tests crew de recherche (criteres, post-processing, commande)
  tools/
    test_kaspr_tool.py   # Tests KasprEnrichTool
    test_pappers_tool.py # Tests PappersSearchTool
    test_gamma_tool.py   # Tests GammaCreateTool (logos, prompt enrichi, polling)
```

## Output CSV

Fichier : `output/company_report.csv` (UTF-8 BOM pour Excel)

23 colonnes par entreprise :
- **Entreprise** : Nom, Site Web, Nationalite, Annee Creation
- **SaaS** : Description solution (max 20 mots)
- **Scoring** : Pertinence (0-100%), Strategie & Angle d'attaque commercial
- **Decideurs** (x3) : Nom, Titre, Email, Telephone, LinkedIn
- **Page Gamma** : URL de la page web Gamma generee

## Scoring WakaStart

| Score | Profil type |
|-------|-------------|
| 90-100% | Sante (besoin HDS) + stack vieillissante |
| 80-90% | Finance/B2B grands comptes + besoin ISO 27001/NIS2 |
| 70-80% | Levee de fonds recente + besoin acceleration dev |
| 60-70% | Stack PHP/Python legacy + pas d'evolution 5+ ans |
| 50-60% | SaaS B2B avec besoin multi-tenant/marque blanche |
| <50% | Pas de SaaS clair ou pas d'ancrage France |

## Tests

179 tests unitaires avec pytest couvrant les 3 crews (analyse, recherche, enrichissement), les 3 tools custom (Kaspr, Pappers, Gamma avec logos dynamiques), le post-processing CSV/JSON et la normalisation d'URLs.

```bash
pytest       # Lancer tous les tests
pytest -v    # Mode verbose
```

## Documentation

- `/docs/Projet WakaStart.pdf` - Description plateforme WakaStart
- `/docs/Protocole Theo.pdf` - Description complete du projet
- `/docs/kaspr.txt` - Documentation API Kaspr
- `/docs/gamma_api.txt` - Documentation API Gamma
- `/docs/pappers_api_v2.yaml` - Specification OpenAPI Pappers v2
