# Hunter.io Integration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remplacer Kaspr par Hunter.io pour l'enrichissement des decideurs dans le crew Analysis (ACT 5).

**Architecture:** Creer un `HunterDomainSearchTool` qui appelle l'endpoint Domain Search de Hunter.io. A partir du domaine de l'entreprise, il retourne jusqu'a 3 decideurs tries par seniority (executive > senior) puis par score de confidence. L'outil remplace `KasprEnrichTool` dans l'agent `lead_generation_expert`.

**Tech Stack:** Python 3.10+, CrewAI (BaseTool, Pydantic), requests, pytest

---

## Task 1: Ajouter les fixtures Hunter dans conftest.py

**Files:**
- Modify: `tests/conftest.py`

**Step 1: Ajouter l'import HunterDomainSearchTool (commenté pour l'instant)**

```python
# En haut du fichier, apres les imports existants (ligne 9)
# from wakastart_leads.crews.analysis.tools.hunter_tool import HunterDomainSearchTool  # TODO: decommenter Task 2
```

**Step 2: Ajouter la fixture mock_hunter_api_key**

```python
# Apres mock_gamma_api_key (ligne 32)

@pytest.fixture()
def mock_hunter_api_key(monkeypatch):
    """Injecte une cle API Hunter de test."""
    monkeypatch.setenv("HUNTER_API_KEY", "test-hunter-key-12345")
```

**Step 3: Ajouter HUNTER_API_KEY dans clear_all_api_keys**

```python
# Modifier clear_all_api_keys pour ajouter la ligne
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
```

**Step 4: Ajouter les fixtures de donnees Hunter**

```python
# Apres les fixtures Gamma (ligne 213)

# ---------------------------------------------------------------------------
# Fixtures de donnees API - Hunter
# ---------------------------------------------------------------------------


@pytest.fixture()
def hunter_domain_search_response():
    """Reponse Hunter Domain Search avec 3 decideurs."""
    return {
        "data": {
            "domain": "stripe.com",
            "organization": "Stripe",
            "emails": [
                {
                    "value": "patrick@stripe.com",
                    "type": "personal",
                    "confidence": 97,
                    "first_name": "Patrick",
                    "last_name": "Collison",
                    "position": "CEO",
                    "seniority": "executive",
                    "department": "executive",
                    "linkedin": "patrickcollison",
                    "phone_number": "+1 555 123 4567",
                },
                {
                    "value": "john@stripe.com",
                    "type": "personal",
                    "confidence": 95,
                    "first_name": "John",
                    "last_name": "Collison",
                    "position": "President",
                    "seniority": "executive",
                    "department": "executive",
                    "linkedin": "johncollison",
                    "phone_number": None,
                },
                {
                    "value": "claire@stripe.com",
                    "type": "personal",
                    "confidence": 90,
                    "first_name": "Claire",
                    "last_name": "Hughes",
                    "position": "COO",
                    "seniority": "senior",
                    "department": "management",
                    "linkedin": "clairehughes",
                    "phone_number": "+1 555 987 6543",
                },
            ],
        },
        "meta": {
            "results": 3,
            "limit": 10,
            "offset": 0,
        },
    }


@pytest.fixture()
def hunter_partial_response():
    """Reponse Hunter avec seulement 1 decideur."""
    return {
        "data": {
            "domain": "smallco.com",
            "organization": "SmallCo",
            "emails": [
                {
                    "value": "ceo@smallco.com",
                    "type": "personal",
                    "confidence": 85,
                    "first_name": "Jean",
                    "last_name": "Dupont",
                    "position": "CEO",
                    "seniority": "executive",
                    "department": "executive",
                    "linkedin": None,
                    "phone_number": None,
                },
            ],
        },
        "meta": {"results": 1, "limit": 10, "offset": 0},
    }


@pytest.fixture()
def hunter_empty_response():
    """Reponse Hunter sans aucun resultat."""
    return {
        "data": {
            "domain": "unknown.com",
            "organization": None,
            "emails": [],
        },
        "meta": {"results": 0, "limit": 10, "offset": 0},
    }


@pytest.fixture()
def hunter_needs_sorting_response():
    """Reponse Hunter avec contacts a trier (senior avant executive dans la liste)."""
    return {
        "data": {
            "domain": "testco.com",
            "organization": "TestCo",
            "emails": [
                {
                    "value": "dev@testco.com",
                    "type": "personal",
                    "confidence": 99,
                    "first_name": "Junior",
                    "last_name": "Dev",
                    "position": "Developer",
                    "seniority": "junior",
                    "department": "it",
                    "linkedin": "juniordev",
                    "phone_number": None,
                },
                {
                    "value": "manager@testco.com",
                    "type": "personal",
                    "confidence": 80,
                    "first_name": "Senior",
                    "last_name": "Manager",
                    "position": "Engineering Manager",
                    "seniority": "senior",
                    "department": "management",
                    "linkedin": "seniormanager",
                    "phone_number": "+1 555 111 2222",
                },
                {
                    "value": "ceo@testco.com",
                    "type": "personal",
                    "confidence": 70,
                    "first_name": "Big",
                    "last_name": "Boss",
                    "position": "CEO",
                    "seniority": "executive",
                    "department": "executive",
                    "linkedin": "bigboss",
                    "phone_number": "+1 555 000 0000",
                },
            ],
        },
        "meta": {"results": 3, "limit": 10, "offset": 0},
    }
```

**Step 5: Verifier que le fichier est syntaxiquement correct**

Run: `python -c "import tests.conftest"`
Expected: Pas d'erreur

**Step 6: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add hunter.io fixtures in conftest"
```

---

## Task 2: Creer le squelette de HunterDomainSearchTool

**Files:**
- Create: `src/wakastart_leads/crews/analysis/tools/hunter_tool.py`

**Step 1: Ecrire le squelette minimal du tool**

```python
"""Hunter.io Domain Search Tool pour l'enrichissement des decideurs."""

import os

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class HunterDomainSearchInput(BaseModel):
    """Input schema pour HunterDomainSearchTool."""

    domain: str = Field(..., description="Domaine de l'entreprise (ex: stripe.com)")
    company_name: str = Field(..., description="Nom de l'entreprise pour contexte")


class HunterDomainSearchTool(BaseTool):
    """
    Recherche les decideurs d'une entreprise via l'API Hunter.io Domain Search.

    A partir du domaine de l'entreprise, retourne jusqu'a 3 decideurs
    avec : nom, prenom, poste, email, telephone, LinkedIn.
    Priorise les C-Level (executive) puis le Management (senior).
    """

    name: str = "hunter_domain_search"
    description: str = (
        "Recherche les decideurs d'une entreprise via Hunter.io. "
        "A partir du domaine (ex: stripe.com), retourne les contacts "
        "C-Level et Management avec leurs coordonnees professionnelles. "
        "Utilise cet outil pour obtenir les decideurs d'une entreprise "
        "a partir de son site web."
    )
    args_schema: type[BaseModel] = HunterDomainSearchInput

    # Priorite de tri par seniority (plus petit = plus prioritaire)
    SENIORITY_PRIORITY: dict[str, int] = {"executive": 1, "senior": 2}

    def _run(self, domain: str, company_name: str) -> str:
        """Execute Hunter Domain Search."""
        # TODO: implementer dans Task 3
        return "Not implemented"
```

**Step 2: Verifier que le module s'importe correctement**

Run: `python -c "from wakastart_leads.crews.analysis.tools.hunter_tool import HunterDomainSearchTool; print('OK')"`
Expected: `OK`

**Step 3: Decommenter l'import dans conftest.py**

Modifier `tests/conftest.py` ligne ~10 :
```python
from wakastart_leads.crews.analysis.tools.hunter_tool import HunterDomainSearchTool
```

**Step 4: Ajouter la fixture hunter_tool dans conftest.py**

```python
# Apres gamma_tool() (ligne 60)

@pytest.fixture()
def hunter_tool():
    return HunterDomainSearchTool()
```

**Step 5: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/hunter_tool.py tests/conftest.py
git commit -m "feat: add hunter_tool skeleton"
```

---

## Task 3: Implementer _build_linkedin_url (TDD)

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/hunter_tool.py`
- Create: `tests/crews/analysis/tools/test_hunter_tool.py`

**Step 1: Ecrire les tests pour _build_linkedin_url**

Creer `tests/crews/analysis/tools/test_hunter_tool.py` :

```python
"""Tests unitaires pour HunterDomainSearchTool."""

import pytest

from wakastart_leads.crews.analysis.tools.hunter_tool import (
    HunterDomainSearchInput,
    HunterDomainSearchTool,
)


# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestHunterToolInstantiation:
    def test_tool_name(self, hunter_tool):
        assert hunter_tool.name == "hunter_domain_search"

    def test_tool_args_schema(self, hunter_tool):
        assert hunter_tool.args_schema is HunterDomainSearchInput


# ===========================================================================
# Tests _build_linkedin_url
# ===========================================================================


class TestBuildLinkedinUrl:
    def test_simple_handle(self, hunter_tool):
        result = hunter_tool._build_linkedin_url("johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_none_handle(self, hunter_tool):
        result = hunter_tool._build_linkedin_url(None)
        assert result == "Non trouve"

    def test_empty_handle(self, hunter_tool):
        result = hunter_tool._build_linkedin_url("")
        assert result == "Non trouve"

    def test_already_full_url(self, hunter_tool):
        result = hunter_tool._build_linkedin_url("https://www.linkedin.com/in/johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_partial_url(self, hunter_tool):
        result = hunter_tool._build_linkedin_url("linkedin.com/in/johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"
```

**Step 2: Lancer les tests pour verifier qu'ils echouent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py -v`
Expected: FAIL (AttributeError: 'HunterDomainSearchTool' object has no attribute '_build_linkedin_url')

**Step 3: Implementer _build_linkedin_url**

Ajouter dans `hunter_tool.py` apres la constante SENIORITY_PRIORITY :

```python
    def _build_linkedin_url(self, handle: str | None) -> str:
        """Construit l'URL LinkedIn complete a partir du handle."""
        if not handle:
            return "Non trouve"

        # Si c'est deja une URL complete ou partielle
        if "linkedin.com" in handle:
            if handle.startswith("http"):
                return handle
            return f"https://www.{handle}" if not handle.startswith("www.") else f"https://{handle}"

        # Sinon, c'est juste le handle
        return f"https://www.linkedin.com/in/{handle}"
```

**Step 4: Lancer les tests pour verifier qu'ils passent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py::TestBuildLinkedinUrl -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/hunter_tool.py tests/crews/analysis/tools/test_hunter_tool.py
git commit -m "feat: implement _build_linkedin_url for hunter tool"
```

---

## Task 4: Implementer _sort_contacts (TDD)

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/hunter_tool.py`
- Modify: `tests/crews/analysis/tools/test_hunter_tool.py`

**Step 1: Ecrire les tests pour _sort_contacts**

Ajouter dans `test_hunter_tool.py` :

```python
# ===========================================================================
# Tests _sort_contacts
# ===========================================================================


class TestSortContacts:
    def test_executive_before_senior(self, hunter_tool):
        """Executive doit etre avant senior meme avec confidence plus basse."""
        contacts = [
            {"seniority": "senior", "confidence": 99, "first_name": "Senior"},
            {"seniority": "executive", "confidence": 70, "first_name": "Exec"},
        ]
        result = hunter_tool._sort_contacts(contacts)
        assert result[0]["first_name"] == "Exec"
        assert result[1]["first_name"] == "Senior"

    def test_same_seniority_sort_by_confidence(self, hunter_tool):
        """A seniority egale, trier par confidence decroissante."""
        contacts = [
            {"seniority": "executive", "confidence": 80, "first_name": "Exec80"},
            {"seniority": "executive", "confidence": 95, "first_name": "Exec95"},
        ]
        result = hunter_tool._sort_contacts(contacts)
        assert result[0]["first_name"] == "Exec95"
        assert result[1]["first_name"] == "Exec80"

    def test_unknown_seniority_last(self, hunter_tool):
        """Seniority inconnue doit etre en dernier."""
        contacts = [
            {"seniority": None, "confidence": 99, "first_name": "Unknown"},
            {"seniority": "senior", "confidence": 50, "first_name": "Senior"},
        ]
        result = hunter_tool._sort_contacts(contacts)
        assert result[0]["first_name"] == "Senior"
        assert result[1]["first_name"] == "Unknown"

    def test_empty_list(self, hunter_tool):
        """Liste vide retourne liste vide."""
        result = hunter_tool._sort_contacts([])
        assert result == []

    def test_limit_to_3(self, hunter_tool):
        """Retourne maximum 3 contacts."""
        contacts = [
            {"seniority": "executive", "confidence": 90, "first_name": f"Exec{i}"}
            for i in range(5)
        ]
        result = hunter_tool._sort_contacts(contacts)
        assert len(result) == 3
```

**Step 2: Lancer les tests pour verifier qu'ils echouent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py::TestSortContacts -v`
Expected: FAIL

**Step 3: Implementer _sort_contacts**

Ajouter dans `hunter_tool.py` :

```python
    def _sort_contacts(self, contacts: list[dict]) -> list[dict]:
        """Trie les contacts par seniority (executive > senior) puis par confidence."""
        sorted_contacts = sorted(
            contacts,
            key=lambda c: (
                self.SENIORITY_PRIORITY.get(c.get("seniority"), 99),
                -c.get("confidence", 0),
            ),
        )
        return sorted_contacts[:3]
```

**Step 4: Lancer les tests pour verifier qu'ils passent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py::TestSortContacts -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/hunter_tool.py tests/crews/analysis/tools/test_hunter_tool.py
git commit -m "feat: implement _sort_contacts for hunter tool"
```

---

## Task 5: Implementer _format_decideurs (TDD)

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/hunter_tool.py`
- Modify: `tests/crews/analysis/tools/test_hunter_tool.py`

**Step 1: Ecrire les tests pour _format_decideurs**

Ajouter dans `test_hunter_tool.py` :

```python
# ===========================================================================
# Tests _format_decideurs
# ===========================================================================


class TestFormatDecideurs:
    def test_full_data(self, hunter_tool):
        """Formate correctement un contact complet."""
        contacts = [
            {
                "first_name": "Patrick",
                "last_name": "Collison",
                "position": "CEO",
                "value": "patrick@stripe.com",
                "phone_number": "+1 555 123 4567",
                "linkedin": "patrickcollison",
            }
        ]
        result = hunter_tool._format_decideurs(contacts, "Stripe")
        assert len(result["decideurs"]) == 3
        d1 = result["decideurs"][0]
        assert d1["nom"] == "Patrick Collison"
        assert d1["titre"] == "CEO"
        assert d1["email"] == "patrick@stripe.com"
        assert d1["telephone"] == "+1 555 123 4567"
        assert d1["linkedin"] == "https://www.linkedin.com/in/patrickcollison"

    def test_missing_fields(self, hunter_tool):
        """Gere les champs manquants avec Non trouve."""
        contacts = [
            {
                "first_name": "Jean",
                "last_name": None,
                "position": None,
                "value": "jean@test.com",
                "phone_number": None,
                "linkedin": None,
            }
        ]
        result = hunter_tool._format_decideurs(contacts, "TestCo")
        d1 = result["decideurs"][0]
        assert d1["nom"] == "Jean"
        assert d1["titre"] == "Non trouve"
        assert d1["telephone"] == "Non trouve"
        assert d1["linkedin"] == "Non trouve"

    def test_pads_to_3_decideurs(self, hunter_tool):
        """Complete toujours a 3 decideurs."""
        contacts = [
            {
                "first_name": "Solo",
                "last_name": "Person",
                "position": "CEO",
                "value": "solo@test.com",
                "phone_number": None,
                "linkedin": None,
            }
        ]
        result = hunter_tool._format_decideurs(contacts, "TestCo")
        assert len(result["decideurs"]) == 3
        assert result["decideurs"][0]["nom"] == "Solo Person"
        assert result["decideurs"][1]["nom"] == "Non trouve"
        assert result["decideurs"][2]["nom"] == "Non trouve"

    def test_empty_contacts(self, hunter_tool):
        """Gere une liste vide de contacts."""
        result = hunter_tool._format_decideurs([], "EmptyCo")
        assert result["contacts_found"] == 0
        assert all(d["nom"] == "Non trouve" for d in result["decideurs"])

    def test_company_in_result(self, hunter_tool):
        """Le nom de l'entreprise est dans le resultat."""
        result = hunter_tool._format_decideurs([], "MyCompany")
        assert result["company"] == "MyCompany"
```

**Step 2: Lancer les tests pour verifier qu'ils echouent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py::TestFormatDecideurs -v`
Expected: FAIL

**Step 3: Implementer _format_decideurs**

Ajouter dans `hunter_tool.py` :

```python
    def _format_decideurs(self, contacts: list[dict], company_name: str) -> dict:
        """Formate les contacts en structure de decideurs pour le CSV."""
        empty_decideur = {
            "nom": "Non trouve",
            "titre": "Non trouve",
            "email": "Non trouve",
            "telephone": "Non trouve",
            "linkedin": "Non trouve",
        }

        decideurs = []
        for contact in contacts[:3]:
            first_name = contact.get("first_name") or ""
            last_name = contact.get("last_name") or ""
            full_name = f"{first_name} {last_name}".strip() or "Non trouve"

            decideurs.append({
                "nom": full_name,
                "titre": contact.get("position") or "Non trouve",
                "email": contact.get("value") or "Non trouve",
                "telephone": contact.get("phone_number") or "Non trouve",
                "linkedin": self._build_linkedin_url(contact.get("linkedin")),
            })

        # Completer a 3 decideurs
        while len(decideurs) < 3:
            decideurs.append(empty_decideur.copy())

        return {
            "company": company_name,
            "decideurs": decideurs,
            "contacts_found": len(contacts),
        }
```

**Step 4: Lancer les tests pour verifier qu'ils passent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py::TestFormatDecideurs -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/hunter_tool.py tests/crews/analysis/tools/test_hunter_tool.py
git commit -m "feat: implement _format_decideurs for hunter tool"
```

---

## Task 6: Implementer _run (TDD)

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/tools/hunter_tool.py`
- Modify: `tests/crews/analysis/tools/test_hunter_tool.py`

**Step 1: Ecrire les tests pour _run**

Ajouter dans `test_hunter_tool.py` :

```python
from unittest.mock import patch

import requests


# ===========================================================================
# Tests _run (mock requests.get + env vars)
# ===========================================================================


class TestHunterRun:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.hunter_tool.requests.get"
    VALID_DOMAIN = "stripe.com"
    VALID_COMPANY = "Stripe"

    def test_missing_api_key(self, hunter_tool, clear_all_api_keys):
        result = hunter_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
        assert "HUNTER_API_KEY non configuree" in result

    def test_success_200(
        self, hunter_tool, mock_hunter_api_key, mock_response, hunter_domain_search_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, hunter_domain_search_response)):
            result = hunter_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Patrick Collison" in result
            assert "patrick@stripe.com" in result
            assert "CEO" in result

    def test_partial_results(
        self, hunter_tool, mock_hunter_api_key, mock_response, hunter_partial_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, hunter_partial_response)):
            result = hunter_tool._run("smallco.com", "SmallCo")
            assert "Jean Dupont" in result
            assert "Non trouve" in result  # Les decideurs manquants

    def test_no_results(
        self, hunter_tool, mock_hunter_api_key, mock_response, hunter_empty_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, hunter_empty_response)):
            result = hunter_tool._run("unknown.com", "Unknown")
            assert "Aucun decideur trouve" in result

    def test_http_401(self, hunter_tool, mock_hunter_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(401, text="Unauthorized")):
            result = hunter_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Cle API Hunter invalide" in result

    def test_http_429(self, hunter_tool, mock_hunter_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(429)):
            result = hunter_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Limite" in result or "limite" in result

    def test_timeout(self, hunter_tool, mock_hunter_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.Timeout):
            result = hunter_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Timeout" in result

    def test_network_error(self, hunter_tool, mock_hunter_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError):
            result = hunter_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "connexion" in result.lower()

    def test_correct_api_params(
        self, hunter_tool, mock_hunter_api_key, mock_response, hunter_domain_search_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, hunter_domain_search_response)) as mock_get:
            hunter_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            call_args = mock_get.call_args
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            assert params["domain"] == self.VALID_DOMAIN
            assert params["type"] == "personal"
            assert "executive" in params["seniority"]
            assert "senior" in params["seniority"]

    def test_sorts_by_seniority(
        self, hunter_tool, mock_hunter_api_key, mock_response, hunter_needs_sorting_response
    ):
        """Verifie que executive est en premier meme si confidence plus basse."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, hunter_needs_sorting_response)):
            result = hunter_tool._run("testco.com", "TestCo")
            # Big Boss (executive, conf 70) doit etre avant Junior Dev (junior, conf 99)
            boss_pos = result.find("Big Boss")
            junior_pos = result.find("Junior Dev")
            # Junior ne doit meme pas apparaitre car on limite a 3 et il y a executive + senior
            assert boss_pos < junior_pos or junior_pos == -1
```

**Step 2: Lancer les tests pour verifier qu'ils echouent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py::TestHunterRun -v`
Expected: FAIL

**Step 3: Implementer _run complet**

Remplacer la methode `_run` dans `hunter_tool.py` :

```python
    def _run(self, domain: str, company_name: str) -> str:
        """Execute Hunter Domain Search."""
        api_key = os.getenv("HUNTER_API_KEY", "").strip()
        if not api_key:
            return "Erreur: HUNTER_API_KEY non configuree dans les variables d'environnement."

        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "domain": domain,
            "api_key": api_key,
            "type": "personal",
            "seniority": "executive,senior",
            "department": "executive,management,it",
            "limit": 10,
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 401:
                return "Erreur: Cle API Hunter invalide ou expiree."
            elif response.status_code == 429:
                return "Erreur: Limite de requetes Hunter atteinte. Reessayez plus tard."
            elif response.status_code != 200:
                return f"Erreur API Hunter (code {response.status_code}): {response.text}"

            data = response.json()
            emails = data.get("data", {}).get("emails", [])

            if not emails:
                return f"Aucun decideur trouve pour {company_name} ({domain})."

            sorted_contacts = self._sort_contacts(emails)
            result = self._format_decideurs(sorted_contacts, company_name)

            return self._format_output(result)

        except requests.exceptions.Timeout:
            return "Erreur: Timeout lors de la connexion a l'API Hunter."
        except requests.exceptions.RequestException as e:
            return f"Erreur de connexion a l'API Hunter: {e!s}"
        except Exception as e:
            return f"Erreur inattendue: {e!s}"

    def _format_output(self, result: dict) -> str:
        """Formate le resultat en string lisible pour l'agent."""
        lines = [f"**Decideurs trouves pour {result['company']}** ({result['contacts_found']} contacts)"]
        lines.append("")

        for i, d in enumerate(result["decideurs"], 1):
            lines.append(f"**Decideur {i}:**")
            lines.append(f"- Nom: {d['nom']}")
            lines.append(f"- Titre: {d['titre']}")
            lines.append(f"- Email: {d['email']}")
            lines.append(f"- Telephone: {d['telephone']}")
            lines.append(f"- LinkedIn: {d['linkedin']}")
            lines.append("")

        return "\n".join(lines)
```

**Step 4: Lancer les tests pour verifier qu'ils passent**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py::TestHunterRun -v`
Expected: 10 passed

**Step 5: Lancer tous les tests du fichier**

Run: `pytest tests/crews/analysis/tools/test_hunter_tool.py -v`
Expected: All passed

**Step 6: Commit**

```bash
git add src/wakastart_leads/crews/analysis/tools/hunter_tool.py tests/crews/analysis/tools/test_hunter_tool.py
git commit -m "feat: implement _run for hunter domain search"
```

---

## Task 7: Integrer Hunter dans le crew Analysis

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/crew.py`

**Step 1: Modifier l'import**

Remplacer ligne 10 :
```python
from .tools.kaspr_tool import KasprEnrichTool
```

Par :
```python
from .tools.hunter_tool import HunterDomainSearchTool
```

**Step 2: Modifier l'agent lead_generation_expert**

Remplacer ligne 102 :
```python
            tools=[SerperDevTool(), ScrapeWebsiteTool(), PappersSearchTool(), KasprEnrichTool()],
```

Par :
```python
            tools=[SerperDevTool(), ScrapeWebsiteTool(), PappersSearchTool(), HunterDomainSearchTool()],
```

**Step 3: Verifier que l'import fonctionne**

Run: `python -c "from wakastart_leads.crews.analysis.crew import AnalysisCrew; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add src/wakastart_leads/crews/analysis/crew.py
git commit -m "feat: replace kaspr with hunter in lead_generation_expert"
```

---

## Task 8: Mettre a jour la description de la tache ACT 5

**Files:**
- Modify: `src/wakastart_leads/crews/analysis/config/tasks.yaml`

**Step 1: Remplacer la description de decision_makers_identification**

Remplacer les lignes 180-228 par :

```yaml
decision_makers_identification:
  description: |-
    ACT 5 - Identification des Decisionnaires via Hunter.io

    Pour chaque entreprise qualifiee, identifier jusqu'a 3 decideurs cles
    en utilisant l'outil hunter_domain_search.

    ETAPE OBLIGATOIRE :
    1. Extraire le DOMAINE du site web de l'entreprise (ex: stripe.com)
       - Depuis l'URL identifiee en ACT 0+1
       - Retirer https://, www., et tout ce qui suit le domaine principal

    2. Appeler hunter_domain_search avec :
       - domain : le domaine extrait (ex: "stripe.com")
       - company_name : le nom de l'entreprise

    3. L'outil retourne directement les 3 meilleurs decideurs avec :
       - Nom complet (Prenom NOM)
       - Titre/Fonction exacte
       - Email professionnel verifie
       - Numero de telephone professionnel
       - URL du profil LinkedIn

    CIBLES PRIORITAIRES (geres automatiquement par Hunter) :
    - CEO / Fondateur / President (Vision strategique)
    - CTO / DSI (Decision technique)
    - COO / VP Engineering / Directeur Produit

    IMPORTANT :
    - UN SEUL appel hunter_domain_search par entreprise
    - L'outil gere le tri et la selection des meilleurs profils
    - Si moins de 3 decideurs trouves, les champs manquants seront "Non trouve"

  expected_output: >
    Pour chaque entreprise, fournir EXACTEMENT ce format pour chaque decideur (jusqu'a 3) :
    - Decideur 1 : [Prenom NOM], [Titre exact], [Email verifie], [Telephone ou Non trouve], [URL LinkedIn complete]
    - Decideur 2 : [Prenom NOM], [Titre exact], [Email verifie], [Telephone ou Non trouve], [URL LinkedIn complete]
    - Decideur 3 : [Prenom NOM], [Titre exact], [Email verifie], [Telephone ou Non trouve], [URL LinkedIn complete]

    Si un decideur n'est pas trouve, indiquer "Non trouve" pour TOUS ses champs.

  agent: lead_generation_expert
  context:
  - extraction_and_macro_filtering
  - origin_identification_and_saas_qualification
  - commercial_analysis
```

**Step 2: Verifier la syntaxe YAML**

Run: `python -c "import yaml; yaml.safe_load(open('src/wakastart_leads/crews/analysis/config/tasks.yaml')); print('YAML OK')"`
Expected: `YAML OK`

**Step 3: Commit**

```bash
git add src/wakastart_leads/crews/analysis/config/tasks.yaml
git commit -m "docs: update ACT 5 task description for hunter.io"
```

---

## Task 9: Lancer tous les tests et verifier

**Files:** (aucune modification)

**Step 1: Lancer tous les tests du projet**

Run: `pytest -v`
Expected: All tests pass

**Step 2: Verifier qu'il n'y a pas d'erreurs d'import**

Run: `python -c "from wakastart_leads.main import cli; print('Main OK')"`
Expected: `Main OK`

**Step 3: Commit final si tout est OK**

```bash
git add -A
git commit -m "chore: hunter.io integration complete" --allow-empty
```

---

## Task 10: Push et verification finale

**Step 1: Push les changements**

Run: `git push`

**Step 2: Verifier le log des commits**

Run: `git log --oneline -10`
Expected: Voir les commits de l'integration Hunter

---

## Resume des fichiers modifies

| Fichier | Action | Description |
|---------|--------|-------------|
| `tests/conftest.py` | Modify | Ajout fixtures Hunter |
| `src/wakastart_leads/crews/analysis/tools/hunter_tool.py` | Create | Nouveau tool HunterDomainSearchTool |
| `tests/crews/analysis/tools/test_hunter_tool.py` | Create | Tests unitaires (~25 tests) |
| `src/wakastart_leads/crews/analysis/crew.py` | Modify | Remplacement Kaspr par Hunter |
| `src/wakastart_leads/crews/analysis/config/tasks.yaml` | Modify | MAJ description ACT 5 |
