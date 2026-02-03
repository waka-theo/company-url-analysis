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
