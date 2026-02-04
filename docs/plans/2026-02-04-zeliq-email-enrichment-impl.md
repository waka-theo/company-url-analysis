# Zeliq Email Enrichment - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ajouter un tool `ZeliqEmailEnrichTool` pour enrichir les emails des decideurs via l'API Zeliq dans ACT5.

**Architecture:** Tool separe de Hunter (decouplage), utilise webhook.site pour gerer l'API asynchrone Zeliq. Zeliq prioritaire sur Hunter pour les emails. Fallback vers email Hunter si Zeliq echoue.

**Tech Stack:** Python 3.10+, CrewAI, requests, pytest

**Design doc:** `docs/plans/2026-02-04-zeliq-email-enrichment-design.md`

---

## Task 1: Creer les fixtures Zeliq dans conftest.py

**Files:**
- Modify: `tests/conftest.py`

**Step 1: Ajouter la fixture mock_zeliq_api_key**

Ajouter apres `mock_hunter_api_key` (ligne 38):

```python
@pytest.fixture()
def mock_zeliq_api_key(monkeypatch):
    """Injecte une cle API Zeliq de test."""
    monkeypatch.setenv("ZELIQ_API_KEY", "test-zeliq-key-12345")
```

**Step 2: Ajouter ZELIQ_API_KEY dans clear_all_api_keys**

Modifier la fixture `clear_all_api_keys` pour inclure ZELIQ_API_KEY:

```python
@pytest.fixture()
def clear_all_api_keys(monkeypatch):
    """Supprime toutes les cles API de l'environnement."""
    monkeypatch.delenv("KASPR_API_KEY", raising=False)
    monkeypatch.delenv("PAPPERS_API_KEY", raising=False)
    monkeypatch.delenv("GAMMA_API_KEY", raising=False)
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    monkeypatch.delenv("ZELIQ_API_KEY", raising=False)
```

**Step 3: Ajouter les fixtures de donnees Zeliq**

Ajouter a la fin du fichier:

```python
# ---------------------------------------------------------------------------
# Fixtures de donnees API - Zeliq
# ---------------------------------------------------------------------------


@pytest.fixture()
def zeliq_success_response():
    """Reponse Zeliq avec email enrichi."""
    return {
        "credit_used": "2",
        "contact": {
            "first_name": "Patrick",
            "last_name": "Collison",
            "domain": "stripe.com",
            "linkedin_url": "https://www.linkedin.com/in/patrickcollison",
            "most_probable_email": "patrick@stripe.com",
            "most_probable_email_status": "safe to send",
            "emails": [
                {"email": "patrick@stripe.com", "status": "safe to send"},
                {"email": "p.collison@stripe.com", "status": "risky"},
            ],
        },
    }


@pytest.fixture()
def zeliq_no_email_response():
    """Reponse Zeliq sans email trouve."""
    return {
        "credit_used": "0",
        "contact": {
            "first_name": "John",
            "last_name": "Doe",
            "domain": None,
            "linkedin_url": "https://www.linkedin.com/in/johndoe",
            "most_probable_email": None,
            "most_probable_email_status": None,
            "emails": [],
        },
    }


@pytest.fixture()
def webhook_site_token_response():
    """Reponse webhook.site pour creation de token."""
    return {
        "uuid": "abc123-def456-ghi789",
    }


@pytest.fixture()
def webhook_site_requests_response(zeliq_success_response):
    """Reponse webhook.site avec les requetes recues."""
    import json

    return {
        "data": [
            {
                "uuid": "req-001",
                "content": json.dumps(zeliq_success_response),
                "created_at": "2026-02-04T10:00:00Z",
            }
        ]
    }


@pytest.fixture()
def webhook_site_empty_response():
    """Reponse webhook.site sans requetes (Zeliq n'a pas encore repondu)."""
    return {"data": []}
```

**Step 4: Run tests to verify fixtures load correctly**

Run: `pytest tests/conftest.py --collect-only`
Expected: No import errors

**Step 5: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add zeliq and webhook.site fixtures"
```

---

## Task 2: Creer le squelette de ZeliqEmailEnrichTool

**Files:**
- Create: `src/wakastart_leads/crews/analysis/tools/zeliq_tool.py`

**Step 1: Creer le fichier avec la structure de base**

```python
"""Zeliq Email Enrichment Tool pour l'enrichissement des emails via LinkedIn."""

import os
from typing import ClassVar

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ZeliqEmailEnrichInput(BaseModel):
    """Input schema pour ZeliqEmailEnrichTool."""

    first_name: str = Field(..., description="Prenom du decideur")
    last_name: str = Field(..., description="Nom du decideur")
    company: str = Field(..., description="Nom ou domaine de l'entreprise")
    linkedin_url: str = Field(..., description="URL LinkedIn complete du decideur")


class ZeliqEmailEnrichTool(BaseTool):
    """
    Enrichit l'email d'un decideur via l'API Zeliq.

    A partir des informations du decideur (nom, prenom, entreprise, LinkedIn),
    retourne l'email le plus probable avec son statut de verification.
    Utilise webhook.site pour gerer l'API asynchrone de Zeliq.
    """

    name: str = "zeliq_email_enrich"
    description: str = (
        "Enrichit l'email d'un decideur via Zeliq. "
        "A partir du prenom, nom, entreprise et URL LinkedIn, "
        "retourne l'email professionnel le plus probable. "
        "Utilise cet outil apres Hunter pour obtenir des emails plus fiables."
    )
    args_schema: type[BaseModel] = ZeliqEmailEnrichInput

    # Configuration
    ZELIQ_API_URL: ClassVar[str] = "https://api.zeliq.com/api/contact/enrich/email"
    WEBHOOK_SITE_URL: ClassVar[str] = "https://webhook.site"
    POLL_INTERVAL: ClassVar[int] = 3  # secondes
    POLL_TIMEOUT: ClassVar[int] = 30  # secondes max

    def _create_webhook_url(self) -> tuple[str, str]:
        """Cree une URL unique via webhook.site. Retourne (webhook_url, token_uuid)."""
        raise NotImplementedError("A implementer dans Task 3")

    def _call_zeliq_api(
        self,
        first_name: str,
        last_name: str,
        company: str,
        linkedin_url: str,
        callback_url: str,
    ) -> bool:
        """Appelle l'API Zeliq. Retourne True si l'appel a reussi."""
        raise NotImplementedError("A implementer dans Task 4")

    def _poll_webhook(self, token_uuid: str) -> dict | None:
        """Poll webhook.site jusqu'a reception de la reponse Zeliq. Retourne les donnees ou None."""
        raise NotImplementedError("A implementer dans Task 5")

    def _run(
        self,
        first_name: str,
        last_name: str,
        company: str,
        linkedin_url: str,
    ) -> str:
        """Execute l'enrichissement email via Zeliq."""
        raise NotImplementedError("A implementer dans Task 6")
```

**Step 2: Run import test**

Run: `python -c "from wakastart_leads.crews.analysis.tools.zeliq_tool import ZeliqEmailEnrichTool; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/zeliq_tool.py
git commit -m "feat: add zeliq tool skeleton"
```

---

## Task 3: Implementer _create_webhook_url avec TDD

**Files:**
- Create: `tests/crews/analysis/tools/test_zeliq_tool.py`
- Modify: `src/wakastart_leads/crews/analysis/tools/zeliq_tool.py`
- Modify: `tests/conftest.py` (ajouter fixture zeliq_tool)

**Step 1: Ajouter la fixture zeliq_tool dans conftest.py**

Ajouter apres la fixture `hunter_tool`:

```python
@pytest.fixture()
def zeliq_tool():
    return ZeliqEmailEnrichTool()
```

Et ajouter l'import en haut du fichier:

```python
from wakastart_leads.crews.analysis.tools.zeliq_tool import ZeliqEmailEnrichTool
```

**Step 2: Ecrire les tests pour _create_webhook_url**

Creer `tests/crews/analysis/tools/test_zeliq_tool.py`:

```python
"""Tests unitaires pour ZeliqEmailEnrichTool."""

from unittest.mock import patch, MagicMock

import pytest
import requests

from wakastart_leads.crews.analysis.tools.zeliq_tool import (
    ZeliqEmailEnrichInput,
    ZeliqEmailEnrichTool,
)


# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestZeliqToolInstantiation:
    def test_tool_name(self, zeliq_tool):
        assert zeliq_tool.name == "zeliq_email_enrich"

    def test_tool_args_schema(self, zeliq_tool):
        assert zeliq_tool.args_schema is ZeliqEmailEnrichInput


# ===========================================================================
# Tests _create_webhook_url
# ===========================================================================


class TestCreateWebhookUrl:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.post"

    def test_returns_url_and_uuid(self, zeliq_tool, mock_response, webhook_site_token_response):
        """Retourne l'URL du webhook et l'UUID du token."""
        with patch(self.PATCH_TARGET, return_value=mock_response(201, webhook_site_token_response)):
            webhook_url, token_uuid = zeliq_tool._create_webhook_url()
            assert webhook_url == "https://webhook.site/abc123-def456-ghi789"
            assert token_uuid == "abc123-def456-ghi789"

    def test_calls_webhook_site_api(self, zeliq_tool, mock_response, webhook_site_token_response):
        """Appelle l'API webhook.site pour creer un token."""
        with patch(self.PATCH_TARGET, return_value=mock_response(201, webhook_site_token_response)) as mock_post:
            zeliq_tool._create_webhook_url()
            mock_post.assert_called_once()
            call_url = mock_post.call_args[0][0]
            assert "webhook.site/token" in call_url

    def test_handles_webhook_site_error(self, zeliq_tool, mock_response):
        """Gere les erreurs de webhook.site."""
        with patch(self.PATCH_TARGET, return_value=mock_response(500)):
            with pytest.raises(RuntimeError, match="webhook.site"):
                zeliq_tool._create_webhook_url()

    def test_handles_network_error(self, zeliq_tool):
        """Gere les erreurs reseau."""
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError):
            with pytest.raises(RuntimeError, match="connexion"):
                zeliq_tool._create_webhook_url()
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestCreateWebhookUrl -v`
Expected: FAIL with "NotImplementedError"

**Step 4: Implementer _create_webhook_url**

Remplacer la methode dans `zeliq_tool.py`:

```python
    def _create_webhook_url(self) -> tuple[str, str]:
        """Cree une URL unique via webhook.site. Retourne (webhook_url, token_uuid)."""
        try:
            response = requests.post(
                f"{self.WEBHOOK_SITE_URL}/token",
                timeout=10,
            )

            if response.status_code != 201:
                raise RuntimeError(
                    f"Erreur webhook.site (code {response.status_code}): impossible de creer le token"
                )

            data = response.json()
            token_uuid = data["uuid"]
            webhook_url = f"{self.WEBHOOK_SITE_URL}/{token_uuid}"

            return webhook_url, token_uuid

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erreur de connexion a webhook.site: {e!s}") from e
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestCreateWebhookUrl -v`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add tests/crews/analysis/tools/test_zeliq_tool.py src/wakastart_leads/crews/analysis/tools/zeliq_tool.py tests/conftest.py
git commit -m "feat: implement _create_webhook_url for zeliq tool"
```

---

## Task 4: Implementer _call_zeliq_api avec TDD

**Files:**
- Modify: `tests/crews/analysis/tools/test_zeliq_tool.py`
- Modify: `src/wakastart_leads/crews/analysis/tools/zeliq_tool.py`

**Step 1: Ecrire les tests pour _call_zeliq_api**

Ajouter dans `test_zeliq_tool.py`:

```python
# ===========================================================================
# Tests _call_zeliq_api
# ===========================================================================


class TestCallZeliqApi:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.post"

    def test_returns_true_on_success(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Retourne True si l'appel API reussit."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, {"status": "processing"})):
            result = zeliq_tool._call_zeliq_api(
                first_name="Patrick",
                last_name="Collison",
                company="stripe.com",
                linkedin_url="https://linkedin.com/in/patrickcollison",
                callback_url="https://webhook.site/abc123",
            )
            assert result is True

    def test_sends_correct_payload(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Envoie le bon payload a l'API Zeliq."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, {})) as mock_post:
            zeliq_tool._call_zeliq_api(
                first_name="Jean",
                last_name="Dupont",
                company="acme.com",
                linkedin_url="https://linkedin.com/in/jeandupont",
                callback_url="https://webhook.site/xyz789",
            )
            call_kwargs = mock_post.call_args.kwargs
            payload = call_kwargs.get("json")
            assert payload["first_name"] == "Jean"
            assert payload["last_name"] == "Dupont"
            assert payload["company"] == "acme.com"
            assert payload["linkedin_url"] == "https://linkedin.com/in/jeandupont"
            assert payload["callback_url"] == "https://webhook.site/xyz789"

    def test_sends_correct_headers(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Envoie le header x-api-key."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, {})) as mock_post:
            zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )
            call_kwargs = mock_post.call_args.kwargs
            headers = call_kwargs.get("headers")
            assert headers["x-api-key"] == "test-zeliq-key-12345"

    def test_missing_api_key_raises_error(self, zeliq_tool, clear_all_api_keys):
        """Leve une erreur si la cle API est absente."""
        with pytest.raises(ValueError, match="ZELIQ_API_KEY"):
            zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )

    def test_handles_401_error(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Gere l'erreur 401 (cle invalide)."""
        with patch(self.PATCH_TARGET, return_value=mock_response(401)):
            result = zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )
            assert result is False

    def test_handles_400_error(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Gere l'erreur 400 (validation)."""
        with patch(self.PATCH_TARGET, return_value=mock_response(400)):
            result = zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )
            assert result is False
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestCallZeliqApi -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implementer _call_zeliq_api**

Remplacer la methode dans `zeliq_tool.py`:

```python
    def _call_zeliq_api(
        self,
        first_name: str,
        last_name: str,
        company: str,
        linkedin_url: str,
        callback_url: str,
    ) -> bool:
        """Appelle l'API Zeliq. Retourne True si l'appel a reussi."""
        api_key = os.getenv("ZELIQ_API_KEY", "").strip()
        if not api_key:
            raise ValueError("ZELIQ_API_KEY non configuree dans les variables d'environnement.")

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "linkedin_url": linkedin_url,
            "callback_url": callback_url,
        }

        try:
            response = requests.post(
                self.ZELIQ_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in (401, 400):
                return False

            return response.status_code == 200

        except requests.exceptions.RequestException:
            return False
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestCallZeliqApi -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add tests/crews/analysis/tools/test_zeliq_tool.py src/wakastart_leads/crews/analysis/tools/zeliq_tool.py
git commit -m "feat: implement _call_zeliq_api for zeliq tool"
```

---

## Task 5: Implementer _poll_webhook avec TDD

**Files:**
- Modify: `tests/crews/analysis/tools/test_zeliq_tool.py`
- Modify: `src/wakastart_leads/crews/analysis/tools/zeliq_tool.py`

**Step 1: Ecrire les tests pour _poll_webhook**

Ajouter dans `test_zeliq_tool.py`:

```python
# ===========================================================================
# Tests _poll_webhook
# ===========================================================================


class TestPollWebhook:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.get"
    PATCH_SLEEP = "wakastart_leads.crews.analysis.tools.zeliq_tool.time.sleep"

    def test_returns_data_when_received(
        self, zeliq_tool, mock_response, webhook_site_requests_response
    ):
        """Retourne les donnees quand le webhook recoit une reponse."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, webhook_site_requests_response)):
            with patch(self.PATCH_SLEEP):
                result = zeliq_tool._poll_webhook("abc123-def456-ghi789")
                assert result is not None
                assert result["contact"]["most_probable_email"] == "patrick@stripe.com"

    def test_polls_until_data_received(
        self, zeliq_tool, mock_response, webhook_site_empty_response, webhook_site_requests_response
    ):
        """Poll plusieurs fois jusqu'a reception des donnees."""
        responses = [
            mock_response(200, webhook_site_empty_response),
            mock_response(200, webhook_site_empty_response),
            mock_response(200, webhook_site_requests_response),
        ]
        with patch(self.PATCH_TARGET, side_effect=responses):
            with patch(self.PATCH_SLEEP) as mock_sleep:
                result = zeliq_tool._poll_webhook("abc123")
                assert result is not None
                assert mock_sleep.call_count == 2  # 2 attentes avant succes

    def test_returns_none_on_timeout(self, zeliq_tool, mock_response, webhook_site_empty_response):
        """Retourne None apres timeout."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, webhook_site_empty_response)):
            with patch(self.PATCH_SLEEP):
                # Simuler un timeout en forcant le nombre max d'iterations
                zeliq_tool.POLL_TIMEOUT = 3
                zeliq_tool.POLL_INTERVAL = 1
                result = zeliq_tool._poll_webhook("abc123")
                assert result is None

    def test_calls_correct_endpoint(self, zeliq_tool, mock_response, webhook_site_requests_response):
        """Appelle le bon endpoint webhook.site."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, webhook_site_requests_response)) as mock_get:
            with patch(self.PATCH_SLEEP):
                zeliq_tool._poll_webhook("my-token-uuid")
                call_url = mock_get.call_args[0][0]
                assert "webhook.site/token/my-token-uuid/requests" in call_url

    def test_handles_network_error(self, zeliq_tool):
        """Retourne None sur erreur reseau."""
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError):
            with patch(self.PATCH_SLEEP):
                result = zeliq_tool._poll_webhook("abc123")
                assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestPollWebhook -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Ajouter l'import time dans zeliq_tool.py**

Ajouter en haut du fichier:

```python
import time
```

**Step 4: Implementer _poll_webhook**

Remplacer la methode dans `zeliq_tool.py`:

```python
    def _poll_webhook(self, token_uuid: str) -> dict | None:
        """Poll webhook.site jusqu'a reception de la reponse Zeliq. Retourne les donnees ou None."""
        import json

        elapsed = 0
        while elapsed < self.POLL_TIMEOUT:
            try:
                response = requests.get(
                    f"{self.WEBHOOK_SITE_URL}/token/{token_uuid}/requests",
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    requests_list = data.get("data", [])

                    if requests_list:
                        # Prendre la premiere requete (la plus recente)
                        first_request = requests_list[0]
                        content = first_request.get("content", "{}")
                        return json.loads(content)

            except requests.exceptions.RequestException:
                return None
            except json.JSONDecodeError:
                return None

            time.sleep(self.POLL_INTERVAL)
            elapsed += self.POLL_INTERVAL

        return None
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestPollWebhook -v`
Expected: PASS (5 tests)

**Step 6: Commit**

```bash
git add tests/crews/analysis/tools/test_zeliq_tool.py src/wakastart_leads/crews/analysis/tools/zeliq_tool.py
git commit -m "feat: implement _poll_webhook for zeliq tool"
```

---

## Task 6: Implementer _run avec TDD

**Files:**
- Modify: `tests/crews/analysis/tools/test_zeliq_tool.py`
- Modify: `src/wakastart_leads/crews/analysis/tools/zeliq_tool.py`

**Step 1: Ecrire les tests pour _run**

Ajouter dans `test_zeliq_tool.py`:

```python
# ===========================================================================
# Tests _run (integration du workflow complet)
# ===========================================================================


class TestZeliqRun:
    PATCH_POST = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.post"
    PATCH_GET = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.get"
    PATCH_SLEEP = "wakastart_leads.crews.analysis.tools.zeliq_tool.time.sleep"

    def test_success_flow(
        self,
        zeliq_tool,
        mock_zeliq_api_key,
        mock_response,
        webhook_site_token_response,
        webhook_site_requests_response,
    ):
        """Workflow complet reussi."""
        with patch(self.PATCH_POST, side_effect=[
            mock_response(201, webhook_site_token_response),  # create webhook
            mock_response(200, {}),  # call zeliq
        ]):
            with patch(self.PATCH_GET, return_value=mock_response(200, webhook_site_requests_response)):
                with patch(self.PATCH_SLEEP):
                    result = zeliq_tool._run(
                        first_name="Patrick",
                        last_name="Collison",
                        company="stripe.com",
                        linkedin_url="https://linkedin.com/in/patrickcollison",
                    )
                    assert "patrick@stripe.com" in result
                    assert "safe to send" in result

    def test_missing_api_key(self, zeliq_tool, clear_all_api_keys):
        """Erreur si cle API absente."""
        result = zeliq_tool._run(
            first_name="Test",
            last_name="User",
            company="test.com",
            linkedin_url="https://linkedin.com/in/test",
        )
        assert "ZELIQ_API_KEY" in result

    def test_webhook_creation_failure(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Gere l'echec de creation du webhook."""
        with patch(self.PATCH_POST, return_value=mock_response(500)):
            result = zeliq_tool._run(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
            )
            assert "webhook" in result.lower() or "erreur" in result.lower()

    def test_zeliq_api_failure(
        self, zeliq_tool, mock_zeliq_api_key, mock_response, webhook_site_token_response
    ):
        """Gere l'echec de l'appel API Zeliq."""
        with patch(self.PATCH_POST, side_effect=[
            mock_response(201, webhook_site_token_response),  # create webhook OK
            mock_response(401),  # call zeliq FAIL
        ]):
            result = zeliq_tool._run(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
            )
            assert "echec" in result.lower() or "erreur" in result.lower()

    def test_timeout_returns_failure_message(
        self, zeliq_tool, mock_zeliq_api_key, mock_response, webhook_site_token_response, webhook_site_empty_response
    ):
        """Retourne un message d'echec apres timeout."""
        with patch(self.PATCH_POST, side_effect=[
            mock_response(201, webhook_site_token_response),
            mock_response(200, {}),
        ]):
            with patch(self.PATCH_GET, return_value=mock_response(200, webhook_site_empty_response)):
                with patch(self.PATCH_SLEEP):
                    zeliq_tool.POLL_TIMEOUT = 3
                    zeliq_tool.POLL_INTERVAL = 1
                    result = zeliq_tool._run(
                        first_name="Test",
                        last_name="User",
                        company="test.com",
                        linkedin_url="https://linkedin.com/in/test",
                    )
                    assert "timeout" in result.lower() or "delai" in result.lower() or "echec" in result.lower()

    def test_no_email_found(
        self, zeliq_tool, mock_zeliq_api_key, mock_response, webhook_site_token_response, zeliq_no_email_response
    ):
        """Gere le cas ou Zeliq ne trouve pas d'email."""
        import json
        webhook_response_with_no_email = {
            "data": [{"uuid": "req-001", "content": json.dumps(zeliq_no_email_response)}]
        }
        with patch(self.PATCH_POST, side_effect=[
            mock_response(201, webhook_site_token_response),
            mock_response(200, {}),
        ]):
            with patch(self.PATCH_GET, return_value=mock_response(200, webhook_response_with_no_email)):
                with patch(self.PATCH_SLEEP):
                    result = zeliq_tool._run(
                        first_name="John",
                        last_name="Doe",
                        company="unknown.com",
                        linkedin_url="https://linkedin.com/in/johndoe",
                    )
                    assert "non trouve" in result.lower() or "aucun email" in result.lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestZeliqRun -v`
Expected: FAIL with "NotImplementedError"

**Step 3: Implementer _run**

Remplacer la methode dans `zeliq_tool.py`:

```python
    def _run(
        self,
        first_name: str,
        last_name: str,
        company: str,
        linkedin_url: str,
    ) -> str:
        """Execute l'enrichissement email via Zeliq."""
        full_name = f"{first_name} {last_name}"

        # Verifier la cle API
        api_key = os.getenv("ZELIQ_API_KEY", "").strip()
        if not api_key:
            return f"Erreur: ZELIQ_API_KEY non configuree. Impossible d'enrichir l'email de {full_name}."

        # Etape 1: Creer le webhook
        try:
            webhook_url, token_uuid = self._create_webhook_url()
        except RuntimeError as e:
            return f"Erreur lors de la creation du webhook pour {full_name}: {e!s}"

        # Etape 2: Appeler l'API Zeliq
        success = self._call_zeliq_api(
            first_name=first_name,
            last_name=last_name,
            company=company,
            linkedin_url=linkedin_url,
            callback_url=webhook_url,
        )

        if not success:
            return f"Echec de l'appel API Zeliq pour {full_name}. Email non enrichi."

        # Etape 3: Poll pour recuperer le resultat
        result = self._poll_webhook(token_uuid)

        if result is None:
            return f"Timeout: Zeliq n'a pas repondu dans le delai imparti pour {full_name}. Email non enrichi."

        # Extraire l'email
        contact = result.get("contact", {})
        email = contact.get("most_probable_email")
        status = contact.get("most_probable_email_status", "unknown")

        if not email:
            return f"Aucun email trouve par Zeliq pour {full_name}."

        return f"Email enrichi pour {full_name}:\n- Email: {email}\n- Statut: {status}"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py::TestZeliqRun -v`
Expected: PASS (6 tests)

**Step 5: Run all zeliq tests**

Run: `pytest tests/crews/analysis/tools/test_zeliq_tool.py -v`
Expected: PASS (23 tests total)

**Step 6: Commit**

```bash
git add tests/crews/analysis/tools/test_zeliq_tool.py src/wakastart_leads/crews/analysis/tools/zeliq_tool.py
git commit -m "feat: implement _run for zeliq tool - complete workflow"
```

---

## Task 7: Integrer ZeliqEmailEnrichTool dans le crew

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/crew.py`

**Step 1: Ajouter l'import**

Ajouter apres l'import de HunterDomainSearchTool:

```python
from .tools.zeliq_tool import ZeliqEmailEnrichTool
```

**Step 2: Ajouter le tool a l'agent lead_generation_expert**

Modifier la methode `lead_generation_expert` (ligne 98-114):

```python
    @agent
    def lead_generation_expert(self) -> Agent:
        """ACT 5 : Expert en Lead Generation & Profiling"""
        return Agent(
            config=self.agents_config["lead_generation_expert"],
            tools=[
                SerperDevTool(),
                ScrapeWebsiteTool(),
                PappersSearchTool(),
                HunterDomainSearchTool(),
                ZeliqEmailEnrichTool(),
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="openai/gpt-4o",
                temperature=0.2,
            ),
        )
```

**Step 3: Verifier l'import**

Run: `python -c "from wakastart_leads.crews.analysis.crew import AnalysisCrew; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/wakastart_leads/crews/analysis/crew.py
git commit -m "feat: add zeliq tool to lead_generation_expert agent"
```

---

## Task 8: Mettre a jour la tache ACT5 dans tasks.yaml

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/config/tasks.yaml`

**Step 1: Mettre a jour la description de decision_makers_identification**

Remplacer la section `decision_makers_identification` (lignes 257-303):

```yaml
decision_makers_identification:
  description: |-
    ACT 5 - Identification des Décisionnaires avec Enrichissement Email Zeliq

    Pour chaque entreprise qualifiée, identifier jusqu'à 3 décideurs clés via Hunter.io,
    puis enrichir leurs emails via Zeliq pour obtenir des adresses plus fiables.

    ÉTAPE 1 - RÉCUPÉRER LE DOMAINE depuis le contexte des tâches précédentes :
    - Extraire le domaine (ex: stripe.com) depuis l'URL du site web identifié en ACT 0+1
    - Ne pas inclure https:// ni www., juste le domaine nu

    ÉTAPE 2 - APPELER OBLIGATOIREMENT l'outil hunter_domain_search avec :
    - domain : Le domaine de l'entreprise (ex: stripe.com)
    - company_name : Le nom de l'entreprise (ex: Stripe)

    L'outil Hunter retourne automatiquement jusqu'à 3 décideurs avec :
    - Nom complet (Prénom NOM)
    - Titre/Fonction exacte
    - Email professionnel (sera enrichi par Zeliq)
    - Numéro de téléphone professionnel
    - URL du profil LinkedIn

    ÉTAPE 3 - ENRICHISSEMENT ZELIQ (OBLIGATOIRE pour chaque décideur avec LinkedIn) :
    Pour CHAQUE décideur ayant une URL LinkedIn valide, appeler zeliq_email_enrich avec :
    - first_name : Prénom du décideur
    - last_name : Nom du décideur
    - company : Le domaine de l'entreprise
    - linkedin_url : L'URL LinkedIn retournée par Hunter

    RÈGLE DE PRIORITÉ EMAIL :
    - Si Zeliq retourne un email → UTILISER l'email Zeliq (plus fiable)
    - Si Zeliq échoue ou timeout → CONSERVER l'email Hunter (fallback)
    - L'email final dans le CSV doit être l'email Zeliq si disponible

    IMPORTANT :
    - Appeler hunter_domain_search UNE SEULE FOIS par entreprise
    - Appeler zeliq_email_enrich pour CHAQUE décideur ayant un LinkedIn valide
    - Ne JAMAIS inventer ou fabriquer un contact
    - Si un décideur n'a pas de LinkedIn, conserver l'email Hunter

  expected_output: >
    Pour chaque entreprise, fournir EXACTEMENT ce format pour chaque décideur (jusqu'à 3) :
    - Décideur 1 : [Prénom NOM], [Titre exact], [Email Zeliq ou Hunter], [Téléphone ou Non trouvé], [URL LinkedIn complète]
    - Décideur 2 : [Prénom NOM], [Titre exact], [Email Zeliq ou Hunter], [Téléphone ou Non trouvé], [URL LinkedIn complète]
    - Décideur 3 : [Prénom NOM], [Titre exact], [Email Zeliq ou Hunter], [Téléphone ou Non trouvé], [URL LinkedIn complète]

    IMPORTANT : Le nom doit TOUJOURS être complet (Prénom NOM).
    L'email doit être celui de Zeliq si disponible, sinon celui de Hunter.
    Si un décideur n'est pas trouvé, indiquer "Non trouvé" pour TOUS ses champs.

  agent: lead_generation_expert
  context:
  - extraction_and_macro_filtering
  - origin_identification_and_saas_qualification
  - commercial_analysis
```

**Step 2: Commit**

```bash
git add src/wakastart_leads/crews/analysis/config/tasks.yaml
git commit -m "feat: update ACT5 task to include zeliq email enrichment"
```

---

## Task 9: Mettre a jour agents.yaml

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/config/agents.yaml`

**Step 1: Mettre a jour le backstory de lead_generation_expert**

Remplacer la section `lead_generation_expert` (lignes 182-232):

```yaml
lead_generation_expert:
  role: Expert en Lead Generation & Profiling
  goal: >
    Identifier les décideurs qui signent ou influencent la décision technique.
    Trouver jusqu'à 3 contacts clés par entreprise avec leurs coordonnées VÉRIFIÉES.
    Utiliser Hunter pour identifier les décideurs, puis Zeliq pour enrichir leurs emails.
  backstory: >
    ACT 5 - Identification des Décisionnaires avec Enrichissement Email

    Vous êtes un expert en génération de leads et profilage de décideurs.
    Votre mission est de trouver les personnes qui signent ou influencent
    la décision technique dans chaque entreprise.

    MÉTHODE DE TRAVAIL OBLIGATOIRE (3 étapes) :

    Étape 1 : RÉCUPÉRER LE DOMAINE DE L'ENTREPRISE
    Les tâches précédentes ont identifié le site web de l'entreprise.
    Extraire le domaine (ex: stripe.com) depuis l'URL du site.

    Étape 2 : APPELER OBLIGATOIREMENT L'OUTIL hunter_domain_search
    Appeler hunter_domain_search avec :
    - domain : Le domaine de l'entreprise (ex: stripe.com)
    - company_name : Le nom de l'entreprise (ex: Stripe)
    Cet outil retourne directement jusqu'à 3 décideurs C-Level et Management
    avec leurs coordonnées professionnelles (email, téléphone, LinkedIn).

    Étape 3 : ENRICHIR LES EMAILS VIA ZELIQ (NOUVEAU)
    Pour CHAQUE décideur ayant une URL LinkedIn valide, appeler zeliq_email_enrich :
    - first_name : Prénom du décideur
    - last_name : Nom du décideur
    - company : Le domaine de l'entreprise
    - linkedin_url : L'URL LinkedIn retournée par Hunter

    RÈGLE DE PRIORITÉ EMAIL :
    Zeliq fournit des emails plus fiables et à jour que Hunter.
    - Si Zeliq retourne un email → L'UTILISER en priorité
    - Si Zeliq échoue → Conserver l'email Hunter comme fallback

    Cibles prioritaires retournées par Hunter :
    1. C-Level :
       - CEO / Fondateur / Président (Vision stratégique)
       - CTO / DSI (Tech & Dette technique)
       - COO (Efficacité opérationnelle)
    2. Profils spécifiques :
       - RSSI (Sécurité/Normes ISO27001/NIS2)
       - VP Engineering
       - Directeur Produit

    RÈGLES ABSOLUES :
    - Ne JAMAIS inventer ou fabriquer un contact
    - Toujours fournir le nom COMPLET (Prénom NOM)
    - Appeler hunter_domain_search UNE SEULE FOIS par entreprise
    - Appeler zeliq_email_enrich pour CHAQUE décideur avec LinkedIn

    Output attendu pour chaque entreprise :
    - Jusqu'à 3 décideurs avec : Nom complet, Titre/Fonction, Email (Zeliq ou Hunter), Téléphone, URL LinkedIn
```

**Step 2: Commit**

```bash
git add src/wakastart_leads/crews/analysis/config/agents.yaml
git commit -m "feat: update lead_generation_expert to use zeliq for email enrichment"
```

---

## Task 10: Mettre a jour la documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `.env.example`

**Step 1: Ajouter la section ZeliqEmailEnrichTool dans CLAUDE.md**

Ajouter apres la section "HunterDomainSearchTool - Methodes internes":

```markdown
### ZeliqEmailEnrichTool - Methodes internes

Le `ZeliqEmailEnrichTool` enrichit les emails des decideurs via l'API Zeliq :

| Methode | Description |
|---------|-------------|
| `_create_webhook_url()` | Cree une URL unique via webhook.site |
| `_call_zeliq_api(...)` | Appel POST a /contact/enrich/email |
| `_poll_webhook(url, timeout)` | Poll webhook.site jusqu'a reponse (max 30s) |
| `_run(first_name, ...)` | Workflow complet : webhook → API → poll → email |

**Flux d'enrichissement** :
```
LinkedIn URL (Hunter) → Zeliq API → webhook.site → Email enrichi
```

**Regle de priorite** : L'email Zeliq remplace l'email Hunter (plus fiable).
Si Zeliq echoue, l'email Hunter est conserve en fallback.
```

**Step 2: Ajouter Zeliq dans le tableau des services externes (CLAUDE.md)**

Ajouter dans la section "Services externes utilises":

```markdown
| **Zeliq** | `https://api.zeliq.com/api` | Enrichissement email via LinkedIn | Requis |
```

**Step 3: Ajouter Zeliq dans README.md**

Dans la section "Services externes", ajouter:

```markdown
| **Zeliq** | Enrichissement | Emails decideurs via LinkedIn | Optionnel (via .env) |
```

**Step 4: Mettre a jour .env.example**

Ajouter apres HUNTER_API_KEY:

```bash
ZELIQ_API_KEY=...           # Optional - Enrichissement email via Zeliq
```

**Step 5: Commit**

```bash
git add CLAUDE.md README.md .env.example
git commit -m "docs: add zeliq tool documentation"
```

---

## Task 11: Run tous les tests et verification finale

**Files:**
- None (verification uniquement)

**Step 1: Run tous les tests**

Run: `pytest -v`
Expected: Tous les tests passent (ancien + nouveau = ~240 tests)

**Step 2: Verifier l'import complet**

Run: `python -c "from wakastart_leads.crews.analysis.crew import AnalysisCrew; c = AnalysisCrew(); print('Crew OK')"`
Expected: `Crew OK`

**Step 3: Verifier la config YAML**

Run: `python -c "import yaml; yaml.safe_load(open('src/wakastart_leads/crews/analysis/config/tasks.yaml')); print('YAML OK')"`
Expected: `YAML OK`

**Step 4: Commit final**

```bash
git add -A
git commit -m "feat: complete zeliq email enrichment integration"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Fixtures conftest.py | - |
| 2 | Squelette ZeliqEmailEnrichTool | - |
| 3 | _create_webhook_url | 4 |
| 4 | _call_zeliq_api | 6 |
| 5 | _poll_webhook | 5 |
| 6 | _run | 6 |
| 7 | Integration crew.py | - |
| 8 | Mise a jour tasks.yaml | - |
| 9 | Mise a jour agents.yaml | - |
| 10 | Documentation | - |
| 11 | Verification finale | - |

**Total nouveaux tests : ~21**
