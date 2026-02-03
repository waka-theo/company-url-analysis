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
