"""Tests unitaires pour SearchCrew (instanciation et configuration)."""

from unittest.mock import MagicMock, patch

import pytest

SM = "company_url_analysis_automation.search_crew"

_AGENT_CFG = {"role": "test", "goal": "test", "backstory": "test"}
_TASK_CFG = {"description": "test", "expected_output": "test"}

SC_AGENTS = ["saas_discovery_scout"]
SC_TASKS = ["search_web_discovery", "search_pappers_validation", "search_saas_deep_scan"]


@pytest.fixture()
def _mock_search_constructors():
    """Mock toutes les dependances externes du SearchCrew."""
    with (
        patch(f"{SM}.LLM", return_value=MagicMock()),
        patch(f"{SM}.Agent", return_value=MagicMock()),
        patch(f"{SM}.Task", return_value=MagicMock()),
        patch(f"{SM}.Crew", return_value=MagicMock()),
        patch(f"{SM}.SerperDevTool", return_value=MagicMock()),
        patch(f"{SM}.ScrapeWebsiteTool", return_value=MagicMock()),
        patch(f"{SM}.PappersSearchTool", return_value=MagicMock()),
    ):
        yield


@pytest.fixture()
def search_crew_instance():
    from crewai.project.crew_base import CrewBaseMeta

    from company_url_analysis_automation.search_crew import SearchCrew

    with patch.object(CrewBaseMeta, "_initialize_crew_instance"):
        instance = SearchCrew()

    instance.agents_config = {name: dict(_AGENT_CFG) for name in SC_AGENTS}
    instance.tasks_config = {name: dict(_TASK_CFG) for name in SC_TASKS}
    instance.log_file = None
    instance.__crew_metadata__ = {
        "original_methods": {},
        "original_tasks": {},
        "original_agents": {},
        "before_kickoff": {},
        "after_kickoff": {},
        "kickoff": {},
    }
    return instance


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


# ===========================================================================
# Tests d'execution des methodes (couvrent les return statements)
# ===========================================================================


@pytest.mark.usefixtures("_mock_search_constructors")
class TestSearchCrewMethods:
    """Verifie que chaque methode retourne un objet."""

    def test_saas_discovery_scout(self, search_crew_instance):
        assert search_crew_instance.saas_discovery_scout() is not None

    def test_search_web_discovery(self, search_crew_instance):
        assert search_crew_instance.search_web_discovery() is not None

    def test_search_pappers_validation(self, search_crew_instance):
        assert search_crew_instance.search_pappers_validation() is not None

    def test_search_saas_deep_scan(self, search_crew_instance):
        assert search_crew_instance.search_saas_deep_scan() is not None

    def test_crew_method(self, search_crew_instance):
        search_crew_instance.agents = [MagicMock()]
        search_crew_instance.tasks = [MagicMock()]
        assert search_crew_instance.crew() is not None

    def test_log_file_default_none(self, search_crew_instance):
        assert search_crew_instance.log_file is None
