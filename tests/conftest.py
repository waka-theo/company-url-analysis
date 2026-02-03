"""Fixtures partagees pour tous les tests."""

from unittest.mock import MagicMock

import pytest

from wakastart_leads.crews.analysis.tools.gamma_tool import GammaCreateTool
from wakastart_leads.crews.analysis.tools.hunter_tool import HunterDomainSearchTool
from wakastart_leads.crews.analysis.tools.kaspr_tool import KasprEnrichTool
from wakastart_leads.shared.tools.pappers_tool import PappersSearchTool

# ---------------------------------------------------------------------------
# Fixtures d'environnement
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_kaspr_api_key(monkeypatch):
    """Injecte une cle API Kaspr de test."""
    monkeypatch.setenv("KASPR_API_KEY", "test-kaspr-key-12345")


@pytest.fixture()
def mock_pappers_api_key(monkeypatch):
    """Injecte une cle API Pappers de test."""
    monkeypatch.setenv("PAPPERS_API_KEY", "test-pappers-key-12345")


@pytest.fixture()
def mock_gamma_api_key(monkeypatch):
    """Injecte une cle API Gamma de test."""
    monkeypatch.setenv("GAMMA_API_KEY", "test-gamma-key-12345")


@pytest.fixture()
def mock_hunter_api_key(monkeypatch):
    """Injecte une cle API Hunter de test."""
    monkeypatch.setenv("HUNTER_API_KEY", "test-hunter-key-12345")


@pytest.fixture()
def clear_all_api_keys(monkeypatch):
    """Supprime toutes les cles API de l'environnement."""
    monkeypatch.delenv("KASPR_API_KEY", raising=False)
    monkeypatch.delenv("PAPPERS_API_KEY", raising=False)
    monkeypatch.delenv("GAMMA_API_KEY", raising=False)
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# Fixtures d'instances d'outils
# ---------------------------------------------------------------------------


@pytest.fixture()
def kaspr_tool():
    return KasprEnrichTool()


@pytest.fixture()
def pappers_tool():
    return PappersSearchTool()


@pytest.fixture()
def gamma_tool():
    return GammaCreateTool()


@pytest.fixture()
def hunter_tool():
    return HunterDomainSearchTool()


# ---------------------------------------------------------------------------
# Factory de mock HTTP
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_response():
    """Factory pour creer un objet Response mocke."""

    def _make_response(status_code: int, json_data: dict | None = None, text: str = ""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        if json_data is not None:
            response.json.return_value = json_data
        else:
            response.json.side_effect = ValueError("No JSON")
        return response

    return _make_response


# ---------------------------------------------------------------------------
# Fixtures de donnees API - Kaspr
# ---------------------------------------------------------------------------


@pytest.fixture()
def kaspr_full_response():
    """Reponse Kaspr complete avec tous les champs."""
    return {
        "profile": {
            "professionalEmails": ["jean.dupont@company.com"],
            "personalEmails": ["jean@gmail.com"],
            "starryProfessionalEmail": "j***@company.com",
            "starryPersonalEmail": "j***@gmail.com",
            "phones": ["+33612345678"],
            "starryPhone": "+336****5678",
            "title": "CTO",
            "company": {"name": "WakaStellar"},
        }
    }


@pytest.fixture()
def kaspr_empty_response():
    """Reponse Kaspr sans emails ni telephones."""
    return {
        "profile": {
            "professionalEmails": [],
            "personalEmails": [],
            "phones": [],
            "title": None,
            "company": None,
        }
    }


@pytest.fixture()
def kaspr_starry_response():
    """Reponse Kaspr avec uniquement les champs starry (masques)."""
    return {
        "profile": {
            "professionalEmails": [],
            "personalEmails": [],
            "starryProfessionalEmail": "j***@company.com",
            "starryPhone": "+336****5678",
            "phones": [],
            "title": "CTO",
            "company": {"name": "TestCorp"},
        }
    }


# ---------------------------------------------------------------------------
# Fixtures de donnees API - Pappers
# ---------------------------------------------------------------------------


@pytest.fixture()
def pappers_company_detail():
    """Reponse Pappers detaillee pour un SIREN."""
    return {
        "siren": "123456789",
        "nom_entreprise": "WakaStellar SAS",
        "denomination": "WakaStellar",
        "forme_juridique": "SAS",
        "date_creation": "2020-01-15",
        "date_immatriculation_rcs": "2020-02-01",
        "entreprise_cessee": False,
        "code_naf": "6201Z",
        "libelle_code_naf": "Programmation informatique",
        "siege": {
            "siret": "12345678900015",
            "adresse_ligne_1": "10 Rue de la Tech",
            "code_postal": "75001",
            "ville": "Paris",
        },
        "finances": {
            "chiffre_affaires": 1500000,
            "resultat": 250000,
        },
        "effectif": "10-19",
        "representants": [
            {"nom_complet": "Jean Dupont", "qualite": "President"},
            {"nom_complet": "Marie Martin", "qualite": "Directeur general"},
            {"prenom": "Pierre", "nom": "Durand", "qualite": "Administrateur"},
        ],
        "beneficiaires_effectifs": [
            {"prenom": "Jean", "nom": "Dupont", "pourcentage_parts": 60},
            {"prenom": "Marie", "nom": "Martin", "pourcentage_parts": 40},
        ],
    }


@pytest.fixture()
def pappers_search_results():
    """Reponse Pappers pour une recherche par nom."""
    return {
        "resultats_nom_entreprise": [
            {
                "nom_entreprise": "WakaStellar SAS",
                "siren": "123456789",
                "siege": {"ville": "Paris"},
                "date_creation": "2020-01-15",
            },
            {
                "nom_entreprise": "WakaTest SARL",
                "siren": "987654321",
                "siege": {"ville": "Lyon"},
                "date_creation": "2019-06-01",
            },
        ]
    }


# ---------------------------------------------------------------------------
# Fixtures de donnees API - Gamma
# ---------------------------------------------------------------------------


@pytest.fixture()
def gamma_generation_response():
    """Reponse Gamma apres creation reussie."""
    return {"generationId": "abc123"}


@pytest.fixture()
def gamma_completed_status():
    """Reponse Gamma pour une generation terminee avec URL."""
    return {"status": "completed", "gammaUrl": "https://gamma.app/docs/abc123"}


# ---------------------------------------------------------------------------
# Factory CSV temporaire
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_csv_file(tmp_path):
    """Factory pour creer un fichier CSV temporaire."""

    def _create(content: str, filename: str = "test.csv") -> str:
        csv_file = tmp_path / filename
        csv_file.write_text(content, encoding="utf-8")
        return str(csv_file)

    return _create


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
