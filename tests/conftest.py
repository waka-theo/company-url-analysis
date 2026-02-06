"""Fixtures partagees pour tous les tests."""

from unittest.mock import MagicMock

import pytest

from wakastart_leads.crews.analysis.tools.apollo_tool import ApolloSearchTool
from wakastart_leads.crews.analysis.tools.gamma_tool import GammaCreateTool
from wakastart_leads.shared.tools.pappers_tool import PappersSearchTool
from wakastart_leads.shared.tools.sirene_tool import SireneSearchTool

# ---------------------------------------------------------------------------
# Fixtures d'environnement
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_apollo_api_key(monkeypatch):
    """Injecte une cle API Apollo de test."""
    monkeypatch.setenv("APOLLO_API_KEY", "test-apollo-key-12345")


@pytest.fixture()
def mock_pappers_api_key(monkeypatch):
    """Injecte une cle API Pappers de test."""
    monkeypatch.setenv("PAPPERS_API_KEY", "test-pappers-key-12345")


@pytest.fixture()
def mock_gamma_api_key(monkeypatch):
    """Injecte une cle API Gamma de test."""
    monkeypatch.setenv("GAMMA_API_KEY", "test-gamma-key-12345")


@pytest.fixture()
def mock_sirene_api_key(monkeypatch):
    """Injecte une cle API Sirene INSEE de test."""
    monkeypatch.setenv("INSEE_SIRENE_API_KEY", "test-sirene-key-12345")


@pytest.fixture()
def clear_all_api_keys(monkeypatch):
    """Supprime toutes les cles API de l'environnement."""
    monkeypatch.delenv("APOLLO_API_KEY", raising=False)
    monkeypatch.delenv("PAPPERS_API_KEY", raising=False)
    monkeypatch.delenv("GAMMA_API_KEY", raising=False)
    monkeypatch.delenv("INSEE_SIRENE_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# Fixtures d'instances d'outils
# ---------------------------------------------------------------------------


@pytest.fixture()
def apollo_tool():
    return ApolloSearchTool()


@pytest.fixture()
def pappers_tool():
    return PappersSearchTool()


@pytest.fixture()
def gamma_tool():
    return GammaCreateTool()


@pytest.fixture()
def sirene_tool():
    return SireneSearchTool()


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
# Fixtures de donnees API - Apollo (People API Search)
# ---------------------------------------------------------------------------


@pytest.fixture()
def apollo_search_response():
    """Reponse Apollo People API Search avec 3 decideurs."""
    return {
        "total_entries": 3,
        "people": [
            {
                "id": "apollo-id-001",
                "first_name": "Patrick",
                "last_name_obfuscated": "Co***n",
                "title": "Co-founder and CEO",
                "last_refreshed_at": "2026-01-15T10:30:00.000Z",
                "has_email": True,
                "has_city": True,
                "has_state": True,
                "has_country": True,
                "has_direct_phone": "Yes",
                "organization": {
                    "name": "Stripe",
                    "has_industry": True,
                    "has_phone": True,
                    "has_city": True,
                    "has_state": True,
                    "has_country": True,
                    "has_zip_code": True,
                    "has_revenue": True,
                    "has_employee_count": True,
                },
            },
            {
                "id": "apollo-id-002",
                "first_name": "John",
                "last_name_obfuscated": "Co***n",
                "title": "President",
                "last_refreshed_at": "2026-01-10T08:00:00.000Z",
                "has_email": True,
                "has_city": True,
                "has_state": True,
                "has_country": True,
                "has_direct_phone": "No",
                "organization": {
                    "name": "Stripe",
                    "has_industry": True,
                    "has_phone": True,
                    "has_city": True,
                    "has_state": True,
                    "has_country": True,
                    "has_zip_code": True,
                    "has_revenue": True,
                    "has_employee_count": True,
                },
            },
            {
                "id": "apollo-id-003",
                "first_name": "David",
                "last_name_obfuscated": "Si***n",
                "title": "CTO",
                "last_refreshed_at": "2026-01-12T14:00:00.000Z",
                "has_email": True,
                "has_city": True,
                "has_state": True,
                "has_country": True,
                "has_direct_phone": "Yes",
                "organization": {
                    "name": "Stripe",
                    "has_industry": True,
                    "has_phone": True,
                    "has_city": True,
                    "has_state": True,
                    "has_country": True,
                    "has_zip_code": True,
                    "has_revenue": True,
                    "has_employee_count": True,
                },
            },
        ],
    }


@pytest.fixture()
def apollo_search_partial_response():
    """Reponse Apollo People API Search avec 1 seul decideur."""
    return {
        "total_entries": 1,
        "people": [
            {
                "id": "apollo-id-010",
                "first_name": "Jean",
                "last_name_obfuscated": "Du***t",
                "title": "CEO",
                "last_refreshed_at": "2026-01-05T10:00:00.000Z",
                "has_email": True,
                "has_city": False,
                "has_state": False,
                "has_country": True,
                "has_direct_phone": "No",
                "organization": {
                    "name": "SmallCo",
                    "has_industry": True,
                    "has_phone": False,
                    "has_city": True,
                    "has_state": True,
                    "has_country": True,
                    "has_zip_code": False,
                    "has_revenue": False,
                    "has_employee_count": True,
                },
            },
        ],
    }


@pytest.fixture()
def apollo_search_empty_response():
    """Reponse Apollo People API Search sans aucun resultat."""
    return {
        "total_entries": 0,
        "people": [],
    }


@pytest.fixture()
def apollo_search_needs_ranking_response():
    """Reponse Apollo avec contacts a trier (director avant CEO dans la liste)."""
    return {
        "total_entries": 3,
        "people": [
            {
                "id": "apollo-id-020",
                "first_name": "Junior",
                "last_name_obfuscated": "De***v",
                "title": "Software Developer",
                "has_email": True,
                "has_direct_phone": "No",
                "organization": {"name": "TestCo"},
            },
            {
                "id": "apollo-id-021",
                "first_name": "Senior",
                "last_name_obfuscated": "Ma***r",
                "title": "Engineering Director",
                "has_email": True,
                "has_direct_phone": "Yes",
                "organization": {"name": "TestCo"},
            },
            {
                "id": "apollo-id-022",
                "first_name": "Big",
                "last_name_obfuscated": "Bo***s",
                "title": "CEO",
                "has_email": True,
                "has_direct_phone": "Yes",
                "organization": {"name": "TestCo"},
            },
        ],
    }


# ---------------------------------------------------------------------------
# Fixtures de donnees API - Apollo (People Enrichment)
# ---------------------------------------------------------------------------


@pytest.fixture()
def apollo_enrich_ceo_response():
    """Reponse Apollo People Enrichment pour un CEO."""
    return {
        "person": {
            "id": "apollo-id-001",
            "first_name": "Patrick",
            "last_name": "Collison",
            "name": "Patrick Collison",
            "title": "Co-founder and CEO",
            "email": "patrick@stripe.com",
            "email_status": "verified",
            "phone_number": None,
            "linkedin_url": "https://www.linkedin.com/in/patrickcollison",
            "organization": {
                "id": "org-stripe",
                "name": "Stripe",
                "domain": "stripe.com",
            },
        }
    }


@pytest.fixture()
def apollo_enrich_president_response():
    """Reponse Apollo People Enrichment pour un President."""
    return {
        "person": {
            "id": "apollo-id-002",
            "first_name": "John",
            "last_name": "Collison",
            "name": "John Collison",
            "title": "President",
            "email": "john@stripe.com",
            "email_status": "verified",
            "phone_number": None,
            "linkedin_url": "https://www.linkedin.com/in/johncollison",
            "organization": {
                "id": "org-stripe",
                "name": "Stripe",
                "domain": "stripe.com",
            },
        }
    }


@pytest.fixture()
def apollo_enrich_cto_response():
    """Reponse Apollo People Enrichment pour un CTO."""
    return {
        "person": {
            "id": "apollo-id-003",
            "first_name": "David",
            "last_name": "Singleton",
            "name": "David Singleton",
            "title": "CTO",
            "email": "david@stripe.com",
            "email_status": "verified",
            "phone_number": None,
            "linkedin_url": "https://www.linkedin.com/in/davidsingleton",
            "organization": {
                "id": "org-stripe",
                "name": "Stripe",
                "domain": "stripe.com",
            },
        }
    }


@pytest.fixture()
def apollo_enrich_partial_response():
    """Reponse Apollo People Enrichment avec champs manquants."""
    return {
        "person": {
            "id": "apollo-id-010",
            "first_name": "Jean",
            "last_name": "Dupont",
            "name": "Jean Dupont",
            "title": "CEO",
            "email": "jean@smallco.com",
            "email_status": "verified",
            "phone_number": None,
            "linkedin_url": None,
            "organization": {
                "id": "org-smallco",
                "name": "SmallCo",
                "domain": "smallco.com",
            },
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
# Fixtures de donnees API - Sirene INSEE
# ---------------------------------------------------------------------------


@pytest.fixture()
def sirene_unite_legale_response():
    """Reponse Sirene pour une recherche par SIREN."""
    return {
        "uniteLegale": {
            "siren": "309634954",
            "dateCreationUniteLegale": "1979-01-01",
            "trancheEffectifsUniteLegale": "41",
            "categorieEntreprise": "GE",
            "periodesUniteLegale": [
                {
                    "denominationUniteLegale": "GOOGLE FRANCE",
                    "categorieJuridiqueUniteLegale": "5720",
                    "activitePrincipaleUniteLegale": "70.10Z",
                    "etatAdministratifUniteLegale": "A",
                }
            ],
        }
    }


@pytest.fixture()
def sirene_search_results_response():
    """Reponse Sirene pour une recherche par nom."""
    return {
        "unitesLegales": [
            {
                "siren": "309634954",
                "dateCreationUniteLegale": "1979-01-01",
                "periodesUniteLegale": [
                    {
                        "denominationUniteLegale": "GOOGLE FRANCE",
                        "etatAdministratifUniteLegale": "A",
                    }
                ],
            },
            {
                "siren": "443061841",
                "dateCreationUniteLegale": "2002-10-01",
                "periodesUniteLegale": [
                    {
                        "denominationUniteLegale": "GOOGLE CLOUD FRANCE",
                        "etatAdministratifUniteLegale": "A",
                    }
                ],
            },
        ]
    }


@pytest.fixture()
def sirene_empty_response():
    """Reponse Sirene sans resultats."""
    return {"unitesLegales": []}


@pytest.fixture()
def sirene_individual_response():
    """Reponse Sirene pour un entrepreneur individuel (nom + prenom)."""
    return {
        "uniteLegale": {
            "siren": "123456789",
            "dateCreationUniteLegale": "2015-03-15",
            "trancheEffectifsUniteLegale": "01",
            "periodesUniteLegale": [
                {
                    "denominationUniteLegale": None,
                    "nomUniteLegale": "DUPONT",
                    "prenomUsuelUniteLegale": "Jean",
                    "categorieJuridiqueUniteLegale": "1000",
                    "activitePrincipaleUniteLegale": "62.01Z",
                    "etatAdministratifUniteLegale": "A",
                }
            ],
        }
    }


@pytest.fixture()
def sirene_ceased_response():
    """Reponse Sirene pour une entreprise cessée."""
    return {
        "uniteLegale": {
            "siren": "999999999",
            "dateCreationUniteLegale": "2010-01-01",
            "periodesUniteLegale": [
                {
                    "denominationUniteLegale": "CLOSED CORP",
                    "categorieJuridiqueUniteLegale": "5499",
                    "etatAdministratifUniteLegale": "C",
                }
            ],
        }
    }
