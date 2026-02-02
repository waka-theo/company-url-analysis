# Amelioration Logos Gamma + Integration Linkener - Plan d'Implementation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ameliorer le dimensionnement des logos dans les pages Gamma et ajouter la creation automatique de liens courts via Linkener.

**Architecture:** Modification de `GammaCreateTool` en 2 phases : (1) enrichissement du prompt avec instructions explicites de dimensionnement des logos, (2) integration de l'API Linkener pour generer des URLs courtes `https://url.wakastart.com/{slug}` apres chaque creation Gamma reussie.

**Tech Stack:** Python 3.10+, CrewAI, requests, pytest, pytest-mock

**Design Reference:** `docs/plans/2026-02-02-gamma-logos-linkener-design.md`

---

## Phase 1 : Amelioration du Prompt Gamma (Logos)

### Task 1.1 : Test - Nouvelles instructions de dimensionnement

**Files:**
- Modify: `tests/crews/analysis/tools/test_gamma_tool.py`

**Step 1: Write the failing test**

Ajouter ce test dans la classe `TestBuildEnhancedPrompt` :

```python
def test_includes_sizing_instructions(self, gamma_tool):
    """Le prompt doit contenir des instructions explicites de dimensionnement."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch(self.PATCH_HEAD, return_value=mock_resp):
        result = gamma_tool._build_enhanced_prompt(
            "Base prompt", "testcorp.com", "TestCorp"
        )
        # Nouvelles instructions attendues
        assert "LOGOS PREMIERE PAGE" in result or "LOGOS" in result
        assert "60-80px" in result or "meme hauteur" in result.lower()
        assert "redimensionner" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestBuildEnhancedPrompt::test_includes_sizing_instructions -v`

Expected: FAIL - les instructions de dimensionnement n'existent pas encore

**Step 3: Commit test (red)**

```bash
git add tests/crews/analysis/tools/test_gamma_tool.py
git commit -m "test: add sizing instructions test for gamma prompt (red)"
```

---

### Task 1.2 : Implementation - Modifier _build_enhanced_prompt

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/gamma_tool.py:128-133`

**Step 1: Replace the image_section block**

Remplacer le bloc actuel (lignes 128-133) :

```python
# AVANT (a supprimer)
image_section = (
    "\n\n"
    "IMAGES POUR LA PREMIERE PAGE (title card) :\n"
    "Placer ces images/logos cote a cote sur la premiere page :\n"
    + "\n".join(image_lines)
)
```

Par :

```python
# APRES (nouveau code)
# Construire l'URL du logo prospect
company_logo_line = ""
if company_logo_url:
    company_logo_line = (
        f"- GAUCHE : Logo {company_name} (redimensionner pour correspondre aux autres) : "
        f"{company_logo_url}\n"
    )

image_section = (
    "\n\n"
    "=== LOGOS PREMIERE PAGE (TITLE CARD) ===\n"
    "Disposition : 3 logos alignes horizontalement, TOUS DE MEME HAUTEUR (environ 60-80px).\n"
    "Les logos doivent etre visuellement equilibres et harmonieux.\n\n"
    "Configuration precise :\n"
    f"{company_logo_line}"
    f"- CENTRE : Image 'Opportunity Analysis' (reference de taille) : {OPPORTUNITY_ANALYSIS_IMAGE_URL}\n"
    f"- DROITE : Logo WakaStellar (meme hauteur) : {WAKASTELLAR_LOGO_URL}\n\n"
    "IMPORTANT : Si le logo de gauche est trop grand ou a un fond blanc visible,\n"
    "le redimensionner et l'adapter pour qu'il s'integre harmonieusement avec les deux autres.\n"
    "Tous les logos doivent avoir une apparence professionnelle et coherente."
)
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestBuildEnhancedPrompt::test_includes_sizing_instructions -v`

Expected: PASS

**Step 3: Run all existing tests to check no regression**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestBuildEnhancedPrompt -v`

Expected: Certains tests existants vont echouer car ils cherchent l'ancien texte

---

### Task 1.3 : Fix - Mettre a jour les tests existants

**Files:**
- Modify: `tests/crews/analysis/tools/test_gamma_tool.py`

**Step 1: Update test_includes_placement_instructions**

Le test cherche "IMAGES POUR LA PREMIERE PAGE" qui n'existe plus. Modifier :

```python
def test_includes_placement_instructions(self, gamma_tool):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch(self.PATCH_HEAD, return_value=mock_resp):
        result = gamma_tool._build_enhanced_prompt(
            "Base prompt", "testcorp.com", "TestCorp"
        )
        # Mise a jour pour le nouveau format
        assert "LOGOS PREMIERE PAGE" in result
        assert "GAUCHE" in result
        assert "CENTRE" in result
        assert "DROITE" in result
```

**Step 2: Update test_correct_payload_uses_enhanced_prompt**

Dans la classe `TestGammaRun`, le test cherche aussi l'ancien texte :

```python
def test_correct_payload_uses_enhanced_prompt(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
    post_response = mock_response(200, {"generationId": "gen_payload"})
    get_response = mock_response(200, gamma_completed_status)
    with (
        patch(self.PATCH_POST, return_value=post_response) as mock_post,
        patch(self.PATCH_GET, return_value=get_response),
        patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        patch(self.PATCH_SLEEP),
    ):
        gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["gammaId"] == GAMMA_TEMPLATE_ID
        assert self.SAMPLE_PROMPT in payload["prompt"]
        # Mise a jour pour le nouveau format
        assert "LOGOS PREMIERE PAGE" in payload["prompt"]
        assert WAKASTELLAR_LOGO_URL in payload["prompt"]
        assert payload["sharingOptions"]["workspaceAccess"] == "view"
        assert payload["sharingOptions"]["externalAccess"] == "view"
```

**Step 3: Run all build_enhanced_prompt tests**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestBuildEnhancedPrompt -v`

Expected: PASS (tous les tests)

**Step 4: Run all gamma_tool tests**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py -v`

Expected: PASS (tous les tests)

**Step 5: Commit**

```bash
git add tests/crews/analysis/tools/test_gamma_tool.py src/wakastart_leads/crews/analysis/tools/gamma_tool.py
git commit -m "feat: improve gamma prompt with explicit logo sizing instructions"
```

---

## Phase 2 : Integration Linkener (URLs courtes)

### Task 2.1 : Test - _sanitize_slug methode

**Files:**
- Modify: `tests/crews/analysis/tools/test_gamma_tool.py`

**Step 1: Add new test class for Linkener**

Ajouter apres la classe `TestGammaRunExceptions` :

```python
# ===========================================================================
# Tests Linkener integration
# ===========================================================================


class TestSanitizeSlug:
    """Tests pour la methode _sanitize_slug."""

    def test_simple_name(self, gamma_tool):
        assert gamma_tool._sanitize_slug("France-Care") == "france-care"

    def test_with_spaces(self, gamma_tool):
        assert gamma_tool._sanitize_slug("Societe Generale") == "societe-generale"

    def test_with_accents(self, gamma_tool):
        assert gamma_tool._sanitize_slug("Cafe Dejeuner") == "cafe-dejeuner"

    def test_with_special_chars(self, gamma_tool):
        assert gamma_tool._sanitize_slug("AI & ML Corp.") == "ai-ml-corp"

    def test_empty_returns_prospect(self, gamma_tool):
        assert gamma_tool._sanitize_slug("") == "prospect"

    def test_only_special_chars_returns_prospect(self, gamma_tool):
        assert gamma_tool._sanitize_slug("@#$%") == "prospect"

    def test_unicode_normalization(self, gamma_tool):
        assert gamma_tool._sanitize_slug("Ecole Superieure") == "ecole-superieure"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestSanitizeSlug -v`

Expected: FAIL - AttributeError: 'GammaCreateTool' object has no attribute '_sanitize_slug'

**Step 3: Commit test (red)**

```bash
git add tests/crews/analysis/tools/test_gamma_tool.py
git commit -m "test: add _sanitize_slug tests for linkener integration (red)"
```

---

### Task 2.2 : Implementation - _sanitize_slug

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/gamma_tool.py`

**Step 1: Add imports at top of file**

Ajouter apres `import time` (ligne 4) :

```python
import re
import unicodedata
```

**Step 2: Add _sanitize_slug method**

Ajouter cette methode dans la classe `GammaCreateTool`, apres `_resolve_company_logo` :

```python
def _sanitize_slug(self, name: str) -> str:
    """Nettoie un nom pour en faire un slug URL-safe."""
    if not name or not name.strip():
        return "prospect"

    # Normaliser les accents (e avec accent -> e)
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")

    # Minuscules
    slug = slug.lower()

    # Remplacer tout ce qui n'est pas alphanum par des tirets
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Supprimer les tirets en debut/fin
    slug = slug.strip("-")

    return slug if slug else "prospect"
```

**Step 3: Run test to verify it passes**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestSanitizeSlug -v`

Expected: PASS (7 tests)

**Step 4: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/gamma_tool.py
git commit -m "feat: add _sanitize_slug method for linkener url generation"
```

---

### Task 2.3 : Test - _get_linkener_token methode

**Files:**
- Modify: `tests/crews/analysis/tools/test_gamma_tool.py`

**Step 1: Add test class for token**

```python
class TestGetLinkenerToken:
    """Tests pour la methode _get_linkener_token."""

    PATCH_POST = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.post"

    def test_success_returns_token(self, gamma_tool, mock_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "access_token_123"
        with patch(self.PATCH_POST, return_value=mock_resp):
            result = gamma_tool._get_linkener_token(
                "https://url.wakastart.com/api", "user", "pass"
            )
            assert result == "access_token_123"

    def test_failure_returns_none(self, gamma_tool, mock_response):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch(self.PATCH_POST, return_value=mock_resp):
            result = gamma_tool._get_linkener_token(
                "https://url.wakastart.com/api", "user", "wrong"
            )
            assert result is None

    def test_timeout_returns_none(self, gamma_tool):
        with patch(self.PATCH_POST, side_effect=requests.exceptions.Timeout):
            result = gamma_tool._get_linkener_token(
                "https://url.wakastart.com/api", "user", "pass"
            )
            assert result is None

    def test_connection_error_returns_none(self, gamma_tool):
        with patch(self.PATCH_POST, side_effect=requests.exceptions.ConnectionError):
            result = gamma_tool._get_linkener_token(
                "https://url.wakastart.com/api", "user", "pass"
            )
            assert result is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestGetLinkenerToken -v`

Expected: FAIL - AttributeError: '_get_linkener_token'

**Step 3: Commit test (red)**

```bash
git add tests/crews/analysis/tools/test_gamma_tool.py
git commit -m "test: add _get_linkener_token tests (red)"
```

---

### Task 2.4 : Implementation - _get_linkener_token

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/gamma_tool.py`

**Step 1: Add _get_linkener_token method**

Ajouter apres `_sanitize_slug` :

```python
def _get_linkener_token(self, api_base: str, username: str, password: str) -> str | None:
    """Obtient un access token Linkener."""
    try:
        response = requests.post(
            f"{api_base}/auth/new_token",
            json={"username": username, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            return response.text.strip()
        print(f"[LINKENER DEBUG] Auth failed: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[LINKENER DEBUG] Auth error: {e}")
    return None
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestGetLinkenerToken -v`

Expected: PASS (4 tests)

**Step 3: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/gamma_tool.py
git commit -m "feat: add _get_linkener_token method for api authentication"
```

---

### Task 2.5 : Test - _create_linkener_url methode

**Files:**
- Modify: `tests/crews/analysis/tools/test_gamma_tool.py`

**Step 1: Add test class**

```python
class TestCreateLinkenerUrl:
    """Tests pour la methode _create_linkener_url."""

    PATCH_POST = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.post"

    def test_missing_env_vars_returns_none(self, gamma_tool, monkeypatch):
        monkeypatch.delenv("LINKENER_API_BASE", raising=False)
        monkeypatch.delenv("LINKENER_USERNAME", raising=False)
        monkeypatch.delenv("LINKENER_PASSWORD", raising=False)
        result = gamma_tool._create_linkener_url(
            "https://gamma.app/docs/abc", "TestCorp"
        )
        assert result is None

    def test_success_returns_short_url(self, gamma_tool, monkeypatch):
        monkeypatch.setenv("LINKENER_API_BASE", "https://url.wakastart.com/api")
        monkeypatch.setenv("LINKENER_USERNAME", "user")
        monkeypatch.setenv("LINKENER_PASSWORD", "pass")

        # Mock auth response
        auth_resp = MagicMock()
        auth_resp.status_code = 200
        auth_resp.text = "token123"

        # Mock create url response
        create_resp = MagicMock()
        create_resp.status_code = 201

        with patch(self.PATCH_POST, side_effect=[auth_resp, create_resp]):
            result = gamma_tool._create_linkener_url(
                "https://gamma.app/docs/abc", "France Care"
            )
            assert result == "https://url.wakastart.com/france-care"

    def test_auth_failure_returns_none(self, gamma_tool, monkeypatch):
        monkeypatch.setenv("LINKENER_API_BASE", "https://url.wakastart.com/api")
        monkeypatch.setenv("LINKENER_USERNAME", "user")
        monkeypatch.setenv("LINKENER_PASSWORD", "wrong")

        auth_resp = MagicMock()
        auth_resp.status_code = 401

        with patch(self.PATCH_POST, return_value=auth_resp):
            result = gamma_tool._create_linkener_url(
                "https://gamma.app/docs/abc", "TestCorp"
            )
            assert result is None

    def test_conflict_409_adds_suffix(self, gamma_tool, monkeypatch):
        monkeypatch.setenv("LINKENER_API_BASE", "https://url.wakastart.com/api")
        monkeypatch.setenv("LINKENER_USERNAME", "user")
        monkeypatch.setenv("LINKENER_PASSWORD", "pass")

        auth_resp = MagicMock()
        auth_resp.status_code = 200
        auth_resp.text = "token123"

        # Premier appel = conflict, deuxieme = success
        conflict_resp = MagicMock()
        conflict_resp.status_code = 409

        success_resp = MagicMock()
        success_resp.status_code = 201

        with patch(self.PATCH_POST, side_effect=[auth_resp, conflict_resp, success_resp]):
            result = gamma_tool._create_linkener_url(
                "https://gamma.app/docs/abc", "TestCorp"
            )
            # Doit retourner une URL avec suffixe
            assert result is not None
            assert result.startswith("https://url.wakastart.com/testcorp")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestCreateLinkenerUrl -v`

Expected: FAIL - AttributeError: '_create_linkener_url'

**Step 3: Commit test (red)**

```bash
git add tests/crews/analysis/tools/test_gamma_tool.py
git commit -m "test: add _create_linkener_url tests (red)"
```

---

### Task 2.6 : Implementation - _create_linkener_url

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/gamma_tool.py`

**Step 1: Add _create_linkener_url method**

Ajouter apres `_get_linkener_token` :

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
    try:
        response = requests.post(
            f"{api_base}/urls/",
            headers={"Authorization": token},
            json={"slug": slug, "url": gamma_url},
            timeout=30,
        )

        base_url = api_base.replace("/api", "")

        if response.status_code in (200, 201):
            print(f"[LINKENER DEBUG] Lien court cree: {base_url}/{slug}")
            return f"{base_url}/{slug}"

        # Gestion slug deja existant (conflict)
        if response.status_code == 409:
            # Ajouter un suffixe numerique
            suffix = int(time.time()) % 1000
            slug_retry = f"{slug}-{suffix}"
            retry_response = requests.post(
                f"{api_base}/urls/",
                headers={"Authorization": token},
                json={"slug": slug_retry, "url": gamma_url},
                timeout=30,
            )
            if retry_response.status_code in (200, 201):
                print(f"[LINKENER DEBUG] Lien court cree (retry): {base_url}/{slug_retry}")
                return f"{base_url}/{slug_retry}"

        print(f"[LINKENER DEBUG] Creation echouee: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"[LINKENER DEBUG] Erreur creation lien: {e}")

    return None
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestCreateLinkenerUrl -v`

Expected: PASS (4 tests)

**Step 3: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/gamma_tool.py
git commit -m "feat: add _create_linkener_url method for short url creation"
```

---

### Task 2.7 : Test - Integration dans _run

**Files:**
- Modify: `tests/crews/analysis/tools/test_gamma_tool.py`

**Step 1: Add integration test**

Ajouter dans la classe `TestGammaRun` :

```python
def test_returns_linkener_url_when_configured(
    self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status, monkeypatch
):
    """Quand Linkener est configure, _run retourne l'URL courte."""
    monkeypatch.setenv("LINKENER_API_BASE", "https://url.wakastart.com/api")
    monkeypatch.setenv("LINKENER_USERNAME", "user")
    monkeypatch.setenv("LINKENER_PASSWORD", "pass")

    post_response = mock_response(200, {"generationId": "gen_link"})
    get_response = mock_response(200, gamma_completed_status)

    # Mock pour Linkener
    auth_resp = MagicMock()
    auth_resp.status_code = 200
    auth_resp.text = "token123"

    create_resp = MagicMock()
    create_resp.status_code = 201

    # L'ordre des POST: Gamma POST, Linkener auth, Linkener create
    with (
        patch(self.PATCH_POST, side_effect=[post_response, auth_resp, create_resp]),
        patch(self.PATCH_GET, return_value=get_response),
        patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        patch(self.PATCH_SLEEP),
    ):
        result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
        assert result == "https://url.wakastart.com/testcorp"

def test_returns_gamma_url_when_linkener_not_configured(
    self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status, monkeypatch
):
    """Sans Linkener, _run retourne l'URL Gamma originale."""
    monkeypatch.delenv("LINKENER_API_BASE", raising=False)
    monkeypatch.delenv("LINKENER_USERNAME", raising=False)
    monkeypatch.delenv("LINKENER_PASSWORD", raising=False)

    post_response = mock_response(200, {"generationId": "gen_no_link"})
    get_response = mock_response(200, gamma_completed_status)

    with (
        patch(self.PATCH_POST, return_value=post_response),
        patch(self.PATCH_GET, return_value=get_response),
        patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        patch(self.PATCH_SLEEP),
    ):
        result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
        assert "gamma.app/docs" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestGammaRun::test_returns_linkener_url_when_configured -v`

Expected: FAIL - le test actuel retourne toujours l'URL Gamma

**Step 3: Commit test (red)**

```bash
git add tests/crews/analysis/tools/test_gamma_tool.py
git commit -m "test: add linkener integration tests in _run (red)"
```

---

### Task 2.8 : Implementation - Modifier _run pour integrer Linkener

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/gamma_tool.py:191`

**Step 1: Modify _run method**

Remplacer la ligne 191 (`return self._poll_generation_status(...)`) par :

```python
gamma_url = self._poll_generation_status(generation_id, api_key)

# Verifier que c'est bien une URL valide (pas un message d'erreur)
if gamma_url.startswith("http"):
    # Tenter de creer un lien court via Linkener
    short_url = self._create_linkener_url(gamma_url, company_name)
    if short_url:
        return short_url
    print("[GAMMA DEBUG] Linkener indisponible, retour URL Gamma")

return gamma_url
```

**Step 2: Run integration test**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestGammaRun::test_returns_linkener_url_when_configured -v`

Expected: PASS

**Step 3: Run fallback test**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py::TestGammaRun::test_returns_gamma_url_when_linkener_not_configured -v`

Expected: PASS

**Step 4: Run all gamma_tool tests**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py -v`

Expected: PASS (tous les tests)

**Step 5: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/gamma_tool.py
git commit -m "feat: integrate linkener url shortener in gamma tool"
```

---

## Phase 3 : Configuration et Documentation

### Task 3.1 : Ajouter les variables d'environnement

**Files:**
- Modify: `.env` (local, not committed)
- Modify: `.env.example` (if exists) or create documentation

**Step 1: Add to .env**

```bash
# Linkener (URL shortener)
LINKENER_API_BASE=https://url.wakastart.com/api
LINKENER_USERNAME=your_username
LINKENER_PASSWORD=your_password
```

**Step 2: Document in CLAUDE.md (optional)**

Si necessaire, ajouter la documentation des nouvelles variables dans CLAUDE.md.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add linkener environment variables documentation"
```

---

## Phase 4 : Validation Finale

### Task 4.1 : Run all tests

**Step 1: Run full test suite**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py -v`

Expected: PASS (tous les tests, ~40+ tests)

**Step 2: Run with coverage**

Run: `pytest tests/crews/analysis/tools/test_gamma_tool.py --cov=wakastart_leads.crews.analysis.tools.gamma_tool --cov-report=term-missing`

Expected: Coverage > 80%

---

### Task 4.2 : Test manuel (optionnel)

**Step 1: Test avec une vraie URL**

Si les credentials Linkener sont configures, tester manuellement :

```bash
python -c "
from wakastart_leads.crews.analysis.tools.gamma_tool import GammaCreateTool
tool = GammaCreateTool()
print(tool._sanitize_slug('France-Care'))
print(tool._sanitize_slug('AI & ML Corp.'))
"
```

Expected:
```
france-care
ai-ml-corp
```

---

### Task 4.3 : Commit final et tag

**Step 1: Final commit**

```bash
git add -A
git commit -m "feat: complete gamma logos improvement and linkener integration

- Improved prompt with explicit logo sizing instructions (60-80px)
- Added Linkener integration for short URLs (https://url.wakastart.com/{slug})
- Graceful fallback to Gamma URL if Linkener unavailable
- Added comprehensive tests for all new methods

Closes: gamma-logos-linkener"
```

---

## Fichiers Modifies (Resume)

| Fichier | Action | Lignes modifiees |
|---------|--------|------------------|
| `src/wakastart_leads/crews/analysis/tools/gamma_tool.py` | Modify | +80 lignes (3 methodes + modification _run) |
| `tests/crews/analysis/tools/test_gamma_tool.py` | Modify | +120 lignes (4 classes de tests) |
| `.env` | Modify | +3 lignes (variables Linkener) |

---

## Checklist de Verification

- [ ] Tests `TestSanitizeSlug` passent (7 tests)
- [ ] Tests `TestGetLinkenerToken` passent (4 tests)
- [ ] Tests `TestCreateLinkenerUrl` passent (4 tests)
- [ ] Tests `TestBuildEnhancedPrompt` passent (4 tests, dont le nouveau)
- [ ] Tests `TestGammaRun` passent (tous, + 2 nouveaux)
- [ ] Tous les tests existants passent sans regression
- [ ] Variables `.env` documentees
- [ ] Pas de `Any` dans le typage
- [ ] Logging avec `[LINKENER DEBUG]` et `[GAMMA DEBUG]`
