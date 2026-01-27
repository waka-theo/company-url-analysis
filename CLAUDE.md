# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Protocole AUTO MASS PROJECT** - Systeme multi-agents CrewAI pour le sourcing et l'enrichissement de leads qualifies pour **WakaStart** (plateforme SaaS de WakaStellar).

**Objectif** : Identifier, analyser et scorer des entreprises ayant une composante SaaS (averee ou cachee) pour determiner leur pertinence vis-a-vis des offres WakaStart.

**Cibles** : StartUp, ScaleUp, Legacy avec composante SaaS
**Geographie** : France (priorite) + International (si lien fort France)

## Commands

```bash
# Install dependencies (creates .venv with Python 3.10)
crewai install

# Run the crew
crewai run

# Train the crew
crewai train <n_iterations> <output_filename>

# Test the crew
crewai test <n_iterations> <openai_model_name>

# Replay from a specific task
crewai replay <task_id>

# Add new dependencies
uv add <package-name>

# Run unit tests
pytest
```

Commandes alternatives via `main.py` :
```bash
python main.py run           # Lance le crew d'analyse
python main.py search        # Lance le crew de recherche d'URLs
python main.py search --criteria path/to/file.json --output output/urls.json
python main.py train N FILE  # Entrainement (N iterations, FILE output)
python main.py replay TASKID # Replay tache specifique
python main.py test N MODEL  # Test crew (N iterations, OpenAI MODEL)
```

## Architecture

Le projet comporte **2 crews** independants :

### Crew 1 : Analyse d'entreprises (6 taches sequentielles)

| ACT | Agent | Modele LLM | Role |
|-----|-------|------------|------|
| 0+1 | `economic_intelligence_analyst` | `openai/gpt-4o` (temp 0.2) | Validation URLs, extraction nom, detection SaaS cache |
| 2+3 | `corporate_analyst_and_saas_qualifier` | `anthropic/claude-sonnet-4-5-20250929` (temp 0.4) | Nationalite, annee creation, qualification technique SaaS |
| 4 | `wakastart_sales_engineer` | `anthropic/claude-sonnet-4-5-20250929` (temp 0.6) | Scoring pertinence (0-100%), angle d'attaque commercial |
| Gamma | `gamma_webpage_creator` | `openai/gpt-4o` (temp 0.3) | Creation page web Gamma avec logos dynamiques |
| 5 | `lead_generation_expert` | `anthropic/claude-sonnet-4-5-20250929` (temp 0.2) | Identification des 3 decideurs + enrichissement Kaspr |
| Final | `data_compiler_and_reporter` | `openai/gpt-4o` (temp 0.1) | Compilation CSV finale (23 colonnes) |

### Crew 2 : Recherche d'URLs (`SearchCrew`)

| Phase | Tache | Role |
|-------|-------|------|
| 1 | `search_web_discovery` | Decouverte web via Serper |
| 2 | `search_pappers_validation` | Validation legale via Pappers |
| 3 | `search_saas_deep_scan` | Verification SaaS approfondie + compilation JSON |

- **Agent** : `saas_discovery_scout` - Expert en Veille Strategique & Detection SaaS
- **Modele** : `anthropic/claude-sonnet-4-5-20250929` (temp 0.3), max 40 iterations
- **Tools** : SerperDevTool, ScrapeWebsiteTool, PappersSearchTool
- **Output** : `output/search_results_raw.json`
- **Input** : `search_criteria.json` (criteres de recherche)

### Key Files

- `src/company_url_analysis_automation/crew.py` - Definitions agents et taches du crew d'analyse (`@agent`, `@task`, `@crew`)
- `src/company_url_analysis_automation/search_crew.py` - Definitions du crew de recherche (`SearchCrew`)
- `src/company_url_analysis_automation/config/agents.yaml` - Roles, goals, backstories des 7 agents
- `src/company_url_analysis_automation/config/tasks.yaml` - Descriptions des 9 taches et outputs attendus
- `src/company_url_analysis_automation/main.py` - Entry point + post-processing CSV et JSON
- `src/company_url_analysis_automation/tools/kaspr_tool.py` - Enrichissement contacts via API Kaspr (email, telephone)
- `src/company_url_analysis_automation/tools/pappers_tool.py` - Donnees legales entreprises via API Pappers
- `src/company_url_analysis_automation/tools/gamma_tool.py` - Creation pages web via API Gamma + resolution logos (Clearbit/Google)

### Tools disponibles par agent

| Agent | Tools |
|-------|-------|
| `economic_intelligence_analyst` | ScrapeWebsiteTool, SerperDevTool, PappersSearchTool |
| `corporate_analyst_and_saas_qualifier` | SerperDevTool, ScrapeWebsiteTool, PappersSearchTool |
| `wakastart_sales_engineer` | SerperDevTool, PappersSearchTool |
| `gamma_webpage_creator` | GammaCreateTool |
| `lead_generation_expert` | SerperDevTool, ScrapeWebsiteTool, PappersSearchTool, KasprEnrichTool |
| `data_compiler_and_reporter` | Aucun (compilation pure) |
| `saas_discovery_scout` | SerperDevTool, ScrapeWebsiteTool, PappersSearchTool |

### Input Format

**Crew d'analyse** : dict `inputs` avec une cle `urls` (voir `main.py`). Fichiers d'entree :
- `liste_test.json` - URLs pour les tests
- `liste.json` - URLs en production

**Crew de recherche** : dict `inputs` avec une cle `search_criteria`. Fichier d'entree :
- `search_criteria.json` - Criteres de recherche au format JSON :
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
Cles optionnelles : `keywords` (str ou list), `sector`, `geographic_zone`, `company_size`, `creation_year_min`, `creation_year_max`, `naf_codes` (list), `exclude_domains` (list), `max_results` (int, defaut 50)

## Output CSV (23 colonnes)

Fichier : `output/company_report.csv` (encode UTF-8 BOM pour Excel)

| Col | Nom | Description |
|-----|-----|-------------|
| A | Societe | Nom commercial de l'entreprise |
| B | Site Web | URL racine (ex: https://wakastellar.com) |
| C | Nationalite | FR, INT (Lien FR), US, UK, etc. |
| D | Annee Creation | YYYY |
| E | Solution SaaS | Description COURTE du produit/service (max 20 mots). Source : ACT 2+3 |
| F | Pertinence (%) | Score 0-100 |
| G | Strategie & Angle | Angle d'attaque commercial WakaStart (PAS la description du produit). Source : ACT 4 (Cameleon) |
| H | Decideur 1 - Nom | Prenom NOM |
| I | Decideur 1 - Titre | CTO, Fondateur, etc. |
| J | Decideur 1 - Email | Email pro verifie (via Kaspr) |
| K | Decideur 1 - Telephone | Telephone pro (via Kaspr) |
| L | Decideur 1 - LinkedIn | URL du profil |
| M-Q | Decideur 2 | Meme structure que Decideur 1 |
| R-V | Decideur 3 | Meme structure que Decideur 1 |
| W | Page Gamma | URL de la page web Gamma generee. Source : gamma_webpage_creation |

### Post-processing CSV (crew d'analyse)

Apres l'execution du crew, `main.py` applique automatiquement un merge intelligent :

1. **Chargement** : `load_existing_csv()` charge le CSV existant (`output/company_report.csv`)
2. **Nettoyage** : Suppression des artefacts markdown (code fences, lignes vides) du CSV temporaire (`output/company_report_new.csv`)
3. **Deduplication** : `normalize_url()` normalise les URLs (suppression protocole, www, trailing slash) pour generer des cles uniques
4. **Merge par URL** : Mise a jour si l'URL existe deja, ajout sinon
5. **Backup automatique** : Sauvegarde avec timestamp avant ecrasement (`output/backups/company_report_YYYYMMDD_HHMMSS.csv`)
6. **Validation colonnes** : Completion avec "Non trouve" si <23 colonnes, troncature si >23
7. **Encodage** : Re-encodage UTF-8 BOM (`utf-8-sig`) pour compatibilite Excel
8. **Nettoyage** : Suppression du fichier temporaire `company_report_new.csv`

### Post-processing Search (crew de recherche)

Apres l'execution du SearchCrew, `post_process_search_results()` applique :

1. **Chargement** : Lecture du JSON brut (`output/search_results_raw.json`)
2. **Nettoyage** : Suppression des artefacts markdown (code fences)
3. **Parsing** : Extraction du JSON array d'URLs
4. **Normalisation** : Ajout `https://` si absent, deduplication
5. **Ecriture** : JSON final timestampe (`output/search_urls_YYYYMMDD_HHMMSS.json`)
6. **Nettoyage** : Suppression du fichier brut temporaire

### Logging

Chaque execution genere un fichier de log structure dans `output/logs/{workflow}/` :
- `output/logs/run/run_YYYYMMDD_HHMMSS.json` pour le crew d'analyse
- `output/logs/search/search_YYYYMMDD_HHMMSS.json` pour le crew de recherche

## Scoring WakaStart (Pertinence)

### Criteres de scoring eleve
- **90-100%** : Sante (besoin HDS) + stack vieillissante
- **80-90%** : Finance/B2B grands comptes + besoin ISO 27001/NIS2
- **70-80%** : Levee de fonds recente + besoin acceleration dev
- **60-70%** : Stack PHP/Python legacy + pas d'evolution depuis 5+ ans
- **50-60%** : SaaS B2B avec besoin multi-tenant/marque blanche
- **<50%** : Pas de composante SaaS claire ou pas d'ancrage France

### Offres WakaStart (leviers de vente)
| Offre | Description | Cible ideale |
|-------|-------------|--------------|
| **Developpement rapide** | 10-25x plus rapide, couts /5 a /15 | StartUp pressee |
| **Waka Migration Pack** | Migration PHP/Python/Go -> Next.js/Nest.js | Legacy avec dette technique |
| **Securite Secure by Design** | ISO 27001, HDS, NIS2 ready | Sante, Finance, B2B grands comptes |
| **Multi-tenant natif** | Gestion reseaux, clients, marques blanches | SaaS B2B |
| **Hebergement Kubernetes** | OVH, scalabilite automatique | ScaleUp en croissance |

### Detection "SaaS Cache"
Ne pas s'arreter a la vitrine. Chercher des indices :
- Offres d'emploi "Dev Fullstack"
- Mention de "Plateforme client", "Portail adherent"
- Levees de fonds pour "R&D"

**Exemple** : France-Care.fr - Conciergerie pour patients. Au premier abord, pas de SaaS. Mais suite a une levee de fonds, ils developpent un CRM specialise.

## Environment

Requires `.env` file with:
```bash
OPENAI_API_KEY=...          # Required - GPT-4o (agents ACT 0+1, Gamma et data_compiler)
ANTHROPIC_API_KEY=...       # Required - Claude Sonnet 4.5 (agents ACT 2+3, ACT 4, ACT 5)
SERPER_API_KEY=...          # Required - Recherche web (SerperDevTool)
PAPPERS_API_KEY=...         # Optional - Donnees legales SIREN/SIRET
KASPR_API_KEY=...           # Optional - Enrichissement leads (email + telephone via LinkedIn)
GAMMA_API_KEY=...           # Optional - Creation pages web via API Gamma
```

### Kaspr API

- Endpoint : `POST https://api.developers.kaspr.io/profile/linkedin`
- Auth : `Authorization: Bearer {KASPR_API_KEY}`
- Headers obligatoires : `Accept: application/json`, `Content-Type: application/json`, `accept-version: v2.0`
- Payload : `{ "id": "linkedin-slug", "name": "Prenom Nom", "dataToGet": ["phone", "workEmail", "directEmail"] }`
- Reponse : structure nestee sous `profile` avec `professionalEmails[]`, `personalEmails[]`, `phones[]`
- Ne fonctionne PAS avec les URLs SalesNavigator
- Credits consommes par requete (plan Starter minimum)

### Gamma API (template-based + logos dynamiques)

- Endpoint : `POST https://public-api.gamma.app/v1.0/generations/from-template`
- Auth : `X-API-KEY: {GAMMA_API_KEY}`
- Template ID : `g_w56csm22x0u632h`
- Inputs obligatoires : `prompt` (texte de personnalisation), `company_name` (nom commercial), `company_domain` (domaine nu sans https/www)
- **Resolution logos** : Le tool resout dynamiquement le logo de l'entreprise via Clearbit (`https://logo.clearbit.com/{domain}`) avec fallback Google Favicon
- **Prompt enrichi** : Injection automatique de 3 images dans la premiere page :
  1. Logo entreprise (via Clearbit/Google)
  2. Image "Opportunity Analysis" (hebergee GitHub)
  3. Logo WakaStellar (hebergee GitHub)
- Workflow : POST → `generationId` → polling GET `/generations/{id}` toutes les 3s (60 tentatives max) → `gammaUrl`
- Reponse finale : URL `https://gamma.app/docs/{generationId}`
- Partage : `workspaceAccess: "view"`, `externalAccess: "view"` (pages accessibles aux clients)
- Timeout : 120s creation, 180s polling total

## Tests

179 tests unitaires avec pytest :

| Fichier | Couverture |
|---------|------------|
| `tests/conftest.py` | Fixtures partagees, mocks API (cles, reponses, instances tools) |
| `tests/test_main.py` | `load_urls()`, `normalize_url()`, `load_existing_csv()`, `post_process_csv()` (59 tests) |
| `tests/test_search_crew.py` | Init SearchCrew, agent, taches, crew config (5 tests) |
| `tests/test_search_main.py` | `load_search_criteria()`, `format_search_criteria()`, `post_process_search_results()`, commande `search()` (85+ tests) |
| `tests/tools/test_kaspr_tool.py` | Init, extraction LinkedIn ID, formatage contacts, appels API, erreurs HTTP |
| `tests/tools/test_pappers_tool.py` | Init, recherche par nom/SIREN, formatage details, erreurs HTTP |
| `tests/tools/test_gamma_tool.py` | Init, inputs, resolution logos (Clearbit/Google), prompt enrichi, appels API, polling, erreurs (39 tests) |

```bash
pytest                    # Lancer tous les tests
pytest tests/test_main.py # Tester uniquement main.py
pytest -v                 # Mode verbose
```

## Documentation de reference

- `/docs/Projet WakaStart.pdf` - Description complete de la plateforme WakaStart
- `/docs/Protocole Theo.pdf` - Description complete du projet
- `/docs/kaspr.txt` - Documentation API Kaspr
- `/docs/gamma_api.txt` - Documentation API Gamma
- `/docs/pappers_api_v2.yaml` - Specification OpenAPI Pappers v2
- `/docs/agent-commercial.md` - Guide agent commercial
