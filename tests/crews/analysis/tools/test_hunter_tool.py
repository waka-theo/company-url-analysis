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
