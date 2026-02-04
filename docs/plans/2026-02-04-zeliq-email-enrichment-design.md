# Design : Intégration Zeliq Email Enrichment

**Date** : 2026-02-04
**Statut** : Validé
**Objectif** : Enrichir les emails des décideurs via l'API Zeliq dans le crew Analysis (ACT5)

---

## Contexte

Le crew Analysis identifie les décideurs via Hunter.io (ACT5 - `decision_makers_identification`). Hunter retourne un email, mais Zeliq peut fournir des emails plus fiables/à jour.

**Décision** : Zeliq est prioritaire sur Hunter pour l'email. Si Zeliq échoue, on conserve l'email Hunter.

---

## Architecture

### Nouveau tool : ZeliqEmailEnrichTool

**Emplacement** : `src/wakastart_leads/crews/analysis/tools/zeliq_tool.py`

**Justification** : Tool séparé (pas intégré dans Hunter) pour limiter les dépendances et faciliter les changements futurs de provider.

### Input/Output

```python
# Input
class ZeliqEmailEnrichInput:
    first_name: str      # Prénom du décideur
    last_name: str       # Nom du décideur
    company: str         # Nom ou domaine de l'entreprise
    linkedin_url: str    # URL LinkedIn complète

# Output (string formaté pour l'agent)
"""
Email enrichi pour Jean DUPONT :
- Email: jean.dupont@company.com
- Statut: safe to send
"""
```

### Gestion du webhook asynchrone

L'API Zeliq est asynchrone (callback_url obligatoire). Stratégie : webhook.site + polling.

```
┌──────────────┐    POST /contact/enrich/email    ┌─────────────┐
│   Zeliq      │ ◄──────────────────────────────── │   Tool      │
│   API        │    callback_url = webhook.site    │             │
└──────────────┘                                   └──────────────┘
       │                                                  │
       │  (Zeliq traite en async)                        │
       ▼                                                  │
┌──────────────┐    GET /token/{uuid}              │
│ webhook.site │ ◄─────────────────────────────────┤ Poll toutes
│              │    (récupère le résultat)         │ les 3 sec
└──────────────┘                                   │ (max 30s)
       │                                                  │
       └──────────────────────────────────────────────────┘
                    Retourne l'email enrichi
```

### Fallback

Si après 30 secondes Zeliq n'a pas répondu → le tool retourne un message d'échec → l'agent conserve l'email Hunter original.

---

## Flux ACT5 modifié

```
NOUVEAU (ACT5):
┌─────────────────────────────────────────────┐
│  1. Hunter Domain Search                    │
│     └─► 3 décideurs (nom, titre, LinkedIn) │
│                                             │
│  2. Pour chaque décideur AVEC LinkedIn :   │
│     └─► Zeliq Email Enrich                 │
│         └─► Remplace email Hunter → Zeliq  │
│                                             │
│  3. Décideurs sans LinkedIn :              │
│     └─► Conserve email Hunter (fallback)   │
└─────────────────────────────────────────────┘
```

---

## Fichiers à modifier

### 1. Nouveau fichier : `crews/analysis/tools/zeliq_tool.py`

Méthodes internes :

| Méthode | Description |
|---------|-------------|
| `_create_webhook_url()` | Crée une URL unique via webhook.site |
| `_call_zeliq_api(...)` | Appel POST à /contact/enrich/email |
| `_poll_webhook(url, timeout)` | Poll webhook.site jusqu'à réponse (max 30s) |
| `_run(first_name, ...)` | Workflow complet : webhook → API → poll → email |

### 2. Modifier : `crews/analysis/config/tasks.yaml`

Tâche `decision_makers_identification` :
- Ajouter étape Zeliq après Hunter
- Préciser la règle de priorité (Zeliq > Hunter)
- Format de sortie inchangé

### 3. Modifier : `crews/analysis/config/agents.yaml`

Agent `lead_generation_expert` :
- Ajouter `zeliq_email_enrich` dans la liste des tools

### 4. Modifier : `crews/analysis/crew.py`

- Importer `ZeliqEmailEnrichTool`
- Instancier le tool dans l'agent `lead_generation_expert`

### 5. Modifier : `.env.example`

```bash
ZELIQ_API_KEY=...  # API Zeliq pour enrichissement email
```

---

## Tests

**Emplacement** : `tests/crews/analysis/tools/test_zeliq_tool.py`

| Classe de test | Tests | Description |
|----------------|-------|-------------|
| `TestZeliqApiCall` | 4-5 | Appel API, headers, payload |
| `TestWebhookPolling` | 4-5 | Création URL webhook.site, polling, timeout |
| `TestZeliqRun` | 5-6 | Flux complet, succès, erreurs API (401, 400), timeout |
| `TestFallbackBehavior` | 2-3 | Comportement quand Zeliq échoue |

**Total estimé** : ~15-18 tests

---

## Documentation à mettre à jour

| Fichier | Modification |
|---------|--------------|
| `CLAUDE.md` | Ajouter section ZeliqEmailEnrichTool |
| `README.md` | Ajouter Zeliq dans le tableau des services externes |

---

## API Zeliq - Référence

**Endpoint** : `POST https://api.zeliq.com/api/contact/enrich/email`

**Auth** : Header `x-api-key: <ZELIQ_API_KEY>`

**Payload** :
```json
{
  "first_name": "Jean",
  "last_name": "Dupont",
  "company": "acme.com",
  "linkedin_url": "https://www.linkedin.com/in/jean-dupont",
  "callback_url": "https://webhook.site/unique-uuid"
}
```

**Réponse** (via webhook) :
```json
{
  "credit_used": "2",
  "contact": {
    "most_probable_email": "jean.dupont@acme.com",
    "most_probable_email_status": "safe to send",
    "emails": [
      {"email": "jean.dupont@acme.com", "status": "safe to send"}
    ]
  }
}
```

---

## Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| webhook.site down | Timeout 30s → fallback email Hunter |
| Zeliq rate limit | Délai entre appels (1s), retry avec backoff |
| Crédits Zeliq épuisés | Log erreur, fallback Hunter |
| LinkedIn URL invalide | Validation format avant appel |
