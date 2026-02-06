# Migration Hunter.io + Zeliq → Apollo.io

**Date** : 2026-02-06
**Scope** : Remplacement complet de Hunter.io et Zeliq par Apollo.io pour la recherche et l'enrichissement des decideurs.

## Contexte

Le systeme actuel utilise 2 providers pour les decideurs :
- **Hunter.io** : recherche de decideurs par domaine (1 appel GET)
- **Zeliq** : enrichissement email via LinkedIn + webhook polling (complexe, fragile)

Apollo.io offre une API unifiee qui couvre les deux besoins avec une meilleure couverture de donnees.

## Architecture

### Flux en 2 etapes

```
Domaine (ex: stripe.com)
        |
        v
+-------------------------------+
|  Etape 1 : People API Search  |  POST /mixed_people/api_search
|  (GRATUIT, 0 credit)          |  Filtres: domain, seniority, titles
|  -> IDs Apollo + titres        |
+-------------------------------+
        |  Top 3 candidats (tries par pertinence)
        v
+-------------------------------+
|  Etape 2 : People Enrichment  |  POST /api/v1/people/match (x3)
|  (PAYANT, 1 credit/appel)     |  Par Apollo ID
|  -> Email, LinkedIn, titre     |
+-------------------------------+
        |
        v
3 decideurs avec coordonnees completes
```

### Parametres de recherche (etape 1)

- `q_organization_domains_list[]` : domaine de l'entreprise
- `person_seniorities[]` : `["owner", "founder", "c_suite", "vp", "head", "director"]`
- `person_titles[]` : `["CTO", "Chief Technology Officer", "Directeur Technique"]`
- `include_similar_titles` : `true`
- `contact_email_status[]` : `["verified", "likely to engage"]`
- `per_page` : 10
- `page` : 1

### Tri des resultats

Priorite seniority :
```
owner (1) > founder (2) > c_suite (3) > vp (4) > head (5) > director (6) > manager (7)
```

A seniority egale, priorite aux profils ayant `has_email=true`.

### Enrichissement (etape 2)

Pour les 3 meilleurs candidats :
- POST `/api/v1/people/match` avec `id` (Apollo ID)
- `reveal_personal_emails` : `true`
- Pas de `reveal_phone_number` (simplifie, pas de webhook)

### Authentification

Header `x-api-key` avec `APOLLO_API_KEY` du `.env`.

## Structure du code

### Nouveau fichier : `apollo_tool.py`

```python
class ApolloSearchInput(BaseModel):
    domain: str       # ex: "stripe.com"
    company_name: str # ex: "Stripe"

class ApolloSearchTool(BaseTool):
    name = "apollo_search"
    # Methodes:
    # _search_people(domain) -> list[dict]
    # _enrich_person(apollo_id) -> dict
    # _rank_candidates(people) -> list[dict]
    # _format_decideurs(enriched, company_name) -> dict
    # _build_linkedin_url(url) -> str
    # _run(domain, company_name) -> str
```

### Constantes

```python
SENIORITY_PRIORITY = {
    "owner": 1, "founder": 2, "c_suite": 3,
    "vp": 4, "head": 5, "director": 6, "manager": 7
}
API_BASE = "https://api.apollo.io/api/v1"
SEARCH_ENDPOINT = "/mixed_people/api_search"
ENRICH_ENDPOINT = "/people/match"
```

## Fichiers impactes

### A creer

| Fichier | Description |
|---------|-------------|
| `crews/analysis/tools/apollo_tool.py` | ApolloSearchTool |
| `tests/crews/analysis/tools/test_apollo_tool.py` | Tests unitaires (~25-30 tests) |

### A modifier

| Fichier | Changement |
|---------|------------|
| `crews/analysis/tools/__init__.py` | Export ApolloSearchTool |
| `crews/analysis/crew.py` | Import Apollo, supprime Hunter + Zeliq |
| `crews/analysis/config/agents.yaml` | Backstory lead_generation_expert -> Apollo |
| `crews/analysis/config/tasks.yaml` | decision_makers_identification -> workflow Apollo |
| `tests/conftest.py` | Fixtures Apollo (remplace Hunter + Zeliq) |

### A supprimer

| Fichier | Raison |
|---------|--------|
| `crews/analysis/tools/hunter_tool.py` | Remplace par Apollo |
| `crews/analysis/tools/zeliq_tool.py` | Remplace par Apollo |
| `tests/crews/analysis/tools/test_hunter_tool.py` | Remplace par test_apollo_tool.py |

### Variables d'environnement

- **Ajouter** : `APOLLO_API_KEY` (deja present dans .env)
- **Obsoletes** : `HUNTER_API_KEY`, `ZELIQ_API_KEY`, `ZELIQ_WEBHOOK_URL`, `ZELIQ_RETRIEVE_URL`

## Format de sortie

Identique a l'existant (compatibilite CSV 23 colonnes) :

```python
{
    "company": "Stripe",
    "decideurs": [
        {
            "nom": "Patrick Collison",
            "titre": "CEO",
            "email": "patrick@stripe.com",
            "telephone": "Non trouve",
            "linkedin": "https://www.linkedin.com/in/patrickcollison"
        },
        # ... jusqu'a 3 decideurs
    ],
    "contacts_found": 2
}
```

## Gestion d'erreurs

| Erreur | Comportement |
|--------|--------------|
| 401 | Cle API invalide |
| 403 | Endpoint non accessible (master key requise) |
| 429 | Rate limit (600 req/heure) |
| Timeout | Message d'erreur explicite |
| 0 resultats search | Aucun decideur trouve |
| Enrichment echoue | Garder les infos partielles du search |

## Cout estimatif

- **Etape 1 (Search)** : 0 credit par entreprise
- **Etape 2 (Enrich)** : 1 credit x 3 decideurs = **3 credits par entreprise**
- Pour 10 entreprises : ~30 credits Apollo
