"""Tests unitaires pour SearchCrew (instanciation et configuration)."""

from unittest.mock import MagicMock, patch

import pytest


class TestSearchCrewImport:
    """Tests d'import du module SearchCrew."""

    def test_import_search_crew(self):
        """Le module search_crew s'importe sans erreur."""
        from company_url_analysis_automation.search_crew import SearchCrew

        assert SearchCrew is not None

    def test_search_crew_is_class(self):
        """SearchCrew est une classe."""
        from company_url_analysis_automation.search_crew import SearchCrew

        assert isinstance(SearchCrew, type)


class TestSearchCrewConfig:
    """Tests de configuration du SearchCrew."""

    def test_has_agent_method(self):
        """SearchCrew a une methode saas_discovery_scout."""
        from company_url_analysis_automation.search_crew import SearchCrew

        assert hasattr(SearchCrew, "saas_discovery_scout")

    def test_has_task_methods(self):
        """SearchCrew a les 3 methodes de taches."""
        from company_url_analysis_automation.search_crew import SearchCrew

        assert hasattr(SearchCrew, "search_web_discovery")
        assert hasattr(SearchCrew, "search_pappers_validation")
        assert hasattr(SearchCrew, "search_saas_deep_scan")

    def test_has_crew_method(self):
        """SearchCrew a une methode crew."""
        from company_url_analysis_automation.search_crew import SearchCrew

        assert hasattr(SearchCrew, "crew")
