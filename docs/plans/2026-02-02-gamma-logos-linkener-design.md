# Design : Amelioration Logos Gamma + Integration Linkener

**Date** : 2026-02-02
**Statut** : Valide
**Auteur** : Claude (brainstorming session)

## Resume

Deux ameliorations au workflow de creation de pages Gamma :
1. **Harmonisation des logos** : Instructions de dimensionnement explicites dans le prompt
2. **Liens personnalises** : Integration Linkener pour creer des URLs courtes `https://url.wakastart.com/{nom}`

---

## 1. Contexte et Problemes

### Probleme 1 : Logos mal dimensionnes

Le code actuel dans `gamma_tool.py` utilise des instructions vagues pour placer les 3 logos sur la premiere page Gamma :
- Logo du prospect (via Unavatar/Clearbit)
- Image "Opportunity Analysis"
- Logo WakaStellar

**Resultat** : Gamma interprete librement ces instructions, produisant des tailles incohérentes (logo prospect souvent trop grand avec fond blanc visible).

### Probleme 2 : URLs Gamma peu memorables

Les URLs Gamma generees sont longues et peu professionnelles :
```
https://gamma.app/docs/Plus-rapide-r123006llp0diwl?mode=doc
```

**Besoin** : URLs courtes et brandees pour les commerciaux :
```
https://url.wakastart.com/france-care
```

---

## 2. Architecture Cible

```
gamma_webpage_creation (task)
         │
         ▼
┌─────────────────────┐
│  GammaCreateTool    │ ◄── Prompt ameliore (dimensionnement logos)
│  (modifie)          │
└──────────┬──────────┘
           │ URL Gamma
           ▼
┌─────────────────────┐
│  Linkener API       │ ◄── Cree le lien court (integre dans le tool)
│  (appel interne)    │
└──────────┬──────────┘
           │ URL courte
           ▼
CSV final (colonne "Page Gamma" = URL courte)
```

---

## 3. Solution 1 : Amelioration du Prompt Gamma

### Code actuel (a remplacer)

```python
# gamma_tool.py, methode _build_enhanced_prompt(), lignes 128-133
image_section = (
    "\n\n"
    "IMAGES POUR LA PREMIERE PAGE (title card) :\n"
    "Placer ces images/logos cote a cote sur la premiere page :\n"
    + "\n".join(image_lines)
)
```

### Nouveau code

```python
image_section = (
    "\n\n"
    "=== LOGOS PREMIERE PAGE (TITLE CARD) ===\n"
    "Disposition : 3 logos alignes horizontalement, TOUS DE MEME HAUTEUR (environ 60-80px).\n"
    "Les logos doivent etre visuellement equilibres et harmonieux.\n\n"
    "Configuration precise :\n"
    f"- GAUCHE : Logo {company_name} (redimensionner pour correspondre aux autres) : {company_logo_url}\n"
    f"- CENTRE : Image 'Opportunity Analysis' (reference de taille) : {OPPORTUNITY_ANALYSIS_IMAGE_URL}\n"
    f"- DROITE : Logo WakaStellar (meme hauteur) : {WAKASTELLAR_LOGO_URL}\n\n"
    "IMPORTANT : Si le logo de gauche est trop grand ou a un fond blanc visible,\n"
    "le redimensionner et l'adapter pour qu'il s'integre harmonieusement avec les deux autres.\n"
    "Tous les logos doivent avoir une apparence professionnelle et coherente."
)
```

### Points cles
- **Hauteur cible explicite** : "60-80px" donne un repere concret a Gamma
- **Reference de taille** : L'image Opportunity Analysis sert de reference
- **Instruction de redimensionnement** : Demande explicite d'adapter le logo prospect
- **Gestion du fond blanc** : Instruction pour les logos avec fond problematique

---

## 4. Solution 2 : Integration Linkener

### API Linkener

**Base URL** : `https://url.wakastart.com/api`

**Authentification** :
1. `POST /auth/new_token` avec `username` + `password` → retourne access_token (plain text)
2. Utiliser l'access_token dans le header `Authorization` pour les appels suivants

**Creation de lien** :
```
POST /urls/
Headers: Authorization: {access_token}
Body: {
    "slug": "france-care",
    "url": "https://gamma.app/docs/xxx"
}
```

### Implementation dans GammaCreateTool

Ajouter une methode privee `_create_linkener_url()` appelee apres la creation Gamma :

```python
def _create_linkener_url(self, gamma_url: str, company_name: str) -> str | None:
    """Cree un lien court Linkener pour l'URL Gamma."""
    api_base = os.getenv("LINKENER_API_BASE", "").strip()
    username = os.getenv("LINKENER_USERNAME", "").strip()
    password = os.getenv("LINKENER_PASSWORD", "").strip()

    if not all([api_base, username, password]):
        print("[LINKENER DEBUG] Variables d'environnement manquantes")
        return None

    # 1. Obtenir un access token
    token = self._get_linkener_token(api_base, username, password)
    if not token:
        return None

    # 2. Nettoyer le nom pour creer le slug
    slug = self._sanitize_slug(company_name)

    # 3. Creer le lien court
    response = requests.post(
        f"{api_base}/urls/",
        headers={"Authorization": token},
        json={"slug": slug, "url": gamma_url},
        timeout=30
    )

    if response.status_code in (200, 201):
        # Construire l'URL finale (sans /api)
        base_url = api_base.replace("/api", "")
        return f"{base_url}/{slug}"

    # Gestion slug deja existant
    if response.status_code == 409:  # Conflict
        slug = f"{slug}-{int(time.time()) % 1000}"
        # Retry avec nouveau slug...

    return None
```

### Methodes utilitaires

```python
def _get_linkener_token(self, api_base: str, username: str, password: str) -> str | None:
    """Obtient un access token Linkener."""
    try:
        response = requests.post(
            f"{api_base}/auth/new_token",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            return response.text.strip()
    except requests.exceptions.RequestException as e:
        print(f"[LINKENER DEBUG] Erreur authentification: {e}")
    return None


def _sanitize_slug(self, name: str) -> str:
    """Nettoie un nom pour en faire un slug URL-safe."""
    import re
    import unicodedata

    # Normaliser les accents
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")

    # Minuscules, remplacer espaces et caracteres speciaux par des tirets
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    return slug or "prospect"
```

### Modification de `_run()`

```python
def _run(self, prompt: str, company_name: str, company_domain: str) -> str:
    # ... code existant ...

    gamma_url = self._poll_generation_status(generation_id, api_key)

    # Verifier que c'est bien une URL valide
    if gamma_url.startswith("http"):
        # NOUVEAU : Creer le lien court automatiquement
        short_url = self._create_linkener_url(gamma_url, company_name)
        if short_url:
            print(f"[GAMMA DEBUG] Lien court cree: {short_url}")
            return short_url
        print("[GAMMA DEBUG] Linkener indisponible, retour URL Gamma")

    return gamma_url  # Fallback sur URL Gamma si Linkener echoue
```

---

## 5. Configuration

### Variables d'environnement (.env)

```bash
# Linkener (URL shortener)
LINKENER_API_BASE=https://url.wakastart.com/api
LINKENER_USERNAME=votre_username
LINKENER_PASSWORD=votre_password
```

### Gestion des erreurs

| Cas | Comportement |
|-----|--------------|
| Variables Linkener manquantes | Log warning, retourne URL Gamma |
| Authentification echouee | Log erreur, retourne URL Gamma |
| Slug deja existant | Ajoute suffixe numerique (ex: `-123`) |
| API Linkener timeout/down | Retourne URL Gamma (fallback gracieux) |
| Nom prospect vide | Utilise slug "prospect" |

---

## 6. Fichiers a Modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `crews/analysis/tools/gamma_tool.py` | Modifier | Prompt ameliore + integration Linkener |
| `.env` | Ajouter | Variables `LINKENER_*` |
| `.env.example` | Ajouter | Documentation des variables |

### Estimation

- **Lignes ajoutees** : ~80 lignes dans `gamma_tool.py`
- **Complexite** : Faible (ajout de methodes, pas de refactoring majeur)
- **Tests** : Ajouter 5-10 tests pour les nouvelles methodes

---

## 7. Output Final

### Avant

| Colonne CSV | Valeur |
|-------------|--------|
| Page Gamma | `https://gamma.app/docs/Plus-rapide-r123006llp0diwl?mode=doc` |

### Apres

| Colonne CSV | Valeur |
|-------------|--------|
| Page Gamma | `https://url.wakastart.com/france-care` |

---

## 8. Risques et Mitigations

| Risque | Probabilite | Impact | Mitigation |
|--------|-------------|--------|------------|
| Gamma ignore les instructions de taille | Moyenne | Faible | Tester et ajuster le wording du prompt |
| Linkener indisponible | Faible | Faible | Fallback automatique sur URL Gamma |
| Conflits de slugs | Moyenne | Faible | Suffixe numerique automatique |
| Rate limiting Linkener | Faible | Moyen | Un seul appel par prospect |

---

## 9. Tests a Ajouter

```python
# tests/crews/analysis/tools/test_gamma_tool.py

def test_sanitize_slug_simple():
    tool = GammaCreateTool()
    assert tool._sanitize_slug("France-Care") == "france-care"

def test_sanitize_slug_accents():
    tool = GammaCreateTool()
    assert tool._sanitize_slug("Societe Generale") == "societe-generale"

def test_sanitize_slug_special_chars():
    tool = GammaCreateTool()
    assert tool._sanitize_slug("AI & ML Corp.") == "ai-ml-corp"

def test_linkener_integration_success(mocker):
    # Mock les appels API Linkener
    ...

def test_linkener_fallback_on_error(mocker):
    # Verifier que l'URL Gamma est retournee si Linkener echoue
    ...
```

---

## 10. Validation

- [x] Vue d'ensemble validee
- [x] Solution logos validee
- [x] Solution Linkener validee
- [x] Integration workflow validee

**Pret pour implementation.**
