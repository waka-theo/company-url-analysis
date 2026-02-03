# Design : Integration Hunter.io pour enrichissement decideurs

**Date** : 2026-02-03
**Statut** : Approuve
**Auteur** : Claude + Theo

## Contexte

Le crew Analysis utilise actuellement `KasprEnrichTool` pour enrichir les contacts des decideurs (email, telephone) a partir de leurs URLs LinkedIn. Cette approche necessite :
1. Que l'agent identifie d'abord les decideurs via scraping
2. Un appel API Kaspr par decideur (3 appels pour 3 decideurs)

Hunter.io propose une approche plus efficace via son endpoint **Domain Search** qui retourne directement les decideurs d'une entreprise avec toutes leurs coordonnees en un seul appel.

## Objectif

Remplacer Kaspr par Hunter.io pour l'enrichissement des decideurs a l'etape ACT 5 (`lead_generation_expert`).

## Decision

### Endpoint API

**Domain Search** : `GET https://api.hunter.io/v2/domain-search`

### Filtres de ciblage

| Parametre | Valeur | Raison |
|-----------|--------|--------|
| `type` | `personal` | Exclut les emails generiques (contact@, info@) |
| `seniority` | `executive,senior` | Cible C-Level et Management |
| `department` | `executive,management,it` | Departements decisionnaires |
| `limit` | `10` | Marge pour avoir du choix apres tri |

### Logique de tri

1. **Priorite seniority** : `executive` avant `senior`
2. **Puis par confidence** : Score Hunter decroissant
3. **Selection** : Les 3 premiers contacts

```python
SENIORITY_PRIORITY = {"executive": 1, "senior": 2}
sorted_contacts = sorted(
    contacts,
    key=lambda c: (SENIORITY_PRIORITY.get(c.get("seniority"), 99), -c.get("confidence", 0))
)
top_3 = sorted_contacts[:3]
```

### Format de sortie

```python
{
    "company": "Stripe",
    "domain": "stripe.com",
    "decideurs": [
        {
            "nom": "Patrick Collison",
            "titre": "CEO",
            "email": "patrick@stripe.com",
            "telephone": "+1 555 123 4567",
            "linkedin": "https://www.linkedin.com/in/patrickcollison"
        },
        # ... jusqu'a 3 decideurs
    ],
    "contacts_found": 2
}
```

### Mapping vers CSV

| Champ Hunter | Colonne CSV |
|--------------|-------------|
| `first_name` + `last_name` | Decideur X - Nom |
| `position` | Decideur X - Titre |
| `value` | Decideur X - Email |
| `phone_number` | Decideur X - Telephone |
| `linkedin` (prefixe) | Decideur X - LinkedIn |

### Gestion des cas edge

- **< 3 decideurs trouves** : Remplir les colonnes disponibles, "Non trouve" pour le reste
- **Aucun resultat** : Tous les champs a "Non trouve"
- **LinkedIn incomplet** : Prefixer avec `https://www.linkedin.com/in/` si necessaire

## Architecture

### Nouveau fichier

```
src/wakastart_leads/crews/analysis/tools/hunter_tool.py
```

### Classes

```python
class HunterDomainSearchInput(BaseModel):
    """Input schema pour HunterDomainSearchTool."""
    domain: str = Field(..., description="Domaine de l'entreprise (ex: stripe.com)")
    company_name: str = Field(..., description="Nom de l'entreprise pour contexte")

class HunterDomainSearchTool(BaseTool):
    """
    Recherche les decideurs d'une entreprise via l'API Hunter.io Domain Search.
    """
    name: str = "hunter_domain_search"
    description: str = (
        "Recherche les decideurs d'une entreprise via Hunter.io. "
        "A partir du domaine (ex: stripe.com), retourne les contacts "
        "C-Level et Management avec leurs coordonnees professionnelles."
    )
    args_schema: type[BaseModel] = HunterDomainSearchInput
```

### Methodes internes

| Methode | Description |
|---------|-------------|
| `_run(domain, company_name)` | Point d'entree principal |
| `_call_hunter_api(domain)` | Appel HTTP a l'API Hunter |
| `_sort_by_seniority(contacts)` | Tri executive > senior > autres |
| `_format_decideurs(contacts)` | Formatage pour le CSV |
| `_build_linkedin_url(handle)` | Prefixe le handle LinkedIn |

## Modifications requises

| Fichier | Action |
|---------|--------|
| `crews/analysis/tools/hunter_tool.py` | Creer |
| `crews/analysis/crew.py` | Modifier - Remplacer Kaspr par Hunter |
| `crews/analysis/config/tasks.yaml` | Modifier - MAJ description ACT 5 |
| `tests/crews/analysis/tools/test_hunter_tool.py` | Creer |

## Workflow avant/apres

### Avant (Kaspr)

```
Agent scrape le site → Identifie 3 decideurs → 3 appels Kaspr (1 par LinkedIn) → Enrichissement
```

### Apres (Hunter)

```
Agent recoit le domaine → 1 appel Hunter Domain Search → 3 decideurs enrichis directement
```

## Avantages

1. **1 appel API au lieu de 3** - Economies de credits et de temps
2. **Moins de dependance au scraping** - Hunter trouve les decideurs
3. **Donnees plus completes** - Tout en une seule reponse
4. **Meilleure fiabilite** - Moins de points de failure

## Variable d'environnement

```bash
HUNTER_API_KEY=...  # Deja presente dans .env
```

## Tests a implementer

- `test_run_success` - Cas nominal avec 3 decideurs
- `test_run_partial_results` - Moins de 3 decideurs
- `test_run_no_results` - Aucun decideur trouve
- `test_run_api_error` - Gestion erreurs API (401, 429, etc.)
- `test_sort_by_seniority` - Tri correct executive > senior
- `test_build_linkedin_url` - Prefixage correct des handles
- `test_missing_api_key` - Erreur si HUNTER_API_KEY absente
