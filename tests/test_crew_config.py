"""Tests unitaires pour CompanyUrlAnalysisAutomationCrew (instanciation des agents, taches et crew)."""

from unittest.mock import MagicMock, patch

import pytest
from crewai.project.crew_base import CrewBaseMeta

M = "company_url_analysis_automation.crew"

# Config minimale suffisante pour que les methodes Agent/Task/Crew ne crashent pas
_AGENT_CFG = {"role": "test", "goal": "test", "backstory": "test"}
_TASK_CFG = {"description": "test", "expected_output": "test"}

AGENTS = [
    "economic_intelligence_analyst",
    "corporate_analyst_and_saas_qualifier",
    "wakastart_sales_engineer",
    "gamma_webpage_creator",
    "lead_generation_expert",
    "data_compiler_and_reporter",
]

TASKS = [
    "extraction_and_macro_filtering",
    "origin_identification_and_saas_qualification",
    "commercial_analysis",
    "gamma_webpage_creation",
    "decision_makers_identification",
    "compile_final_company_analysis_report",
]


@pytest.fixture()
def crew_instance():
    """Cree une instance en bypassant l'init de CrewBaseMeta."""
    from company_url_analysis_automation.crew import CompanyUrlAnalysisAutomationCrew

    with patch.object(CrewBaseMeta, "_initialize_crew_instance"):
        instance = CompanyUrlAnalysisAutomationCrew()

    instance.agents_config = {name: dict(_AGENT_CFG) for name in AGENTS}
    instance.tasks_config = {name: dict(_TASK_CFG) for name in TASKS}
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


@pytest.fixture()
def _mock_constructors():
    """Mock toutes les dependances externes (constructeurs)."""
    with (
        patch(f"{M}.LLM", return_value=MagicMock()),
        patch(f"{M}.Agent", return_value=MagicMock()),
        patch(f"{M}.Task", return_value=MagicMock()),
        patch(f"{M}.Crew", return_value=MagicMock()),
        patch(f"{M}.SerperDevTool", return_value=MagicMock()),
        patch(f"{M}.ScrapeWebsiteTool", return_value=MagicMock()),
        patch(f"{M}.PappersSearchTool", return_value=MagicMock()),
        patch(f"{M}.GammaCreateTool", return_value=MagicMock()),
        patch(f"{M}.KasprEnrichTool", return_value=MagicMock()),
    ):
        yield


# ===========================================================================
# Tests des agents
# ===========================================================================


@pytest.mark.usefixtures("_mock_constructors")
class TestCrewAgents:
    """Verifie que chaque methode @agent retourne un objet."""

    def test_economic_intelligence_analyst(self, crew_instance):
        assert crew_instance.economic_intelligence_analyst() is not None

    def test_corporate_analyst_and_saas_qualifier(self, crew_instance):
        assert crew_instance.corporate_analyst_and_saas_qualifier() is not None

    def test_wakastart_sales_engineer(self, crew_instance):
        assert crew_instance.wakastart_sales_engineer() is not None

    def test_gamma_webpage_creator(self, crew_instance):
        assert crew_instance.gamma_webpage_creator() is not None

    def test_lead_generation_expert(self, crew_instance):
        assert crew_instance.lead_generation_expert() is not None

    def test_data_compiler_and_reporter(self, crew_instance):
        assert crew_instance.data_compiler_and_reporter() is not None


# ===========================================================================
# Tests des taches
# ===========================================================================


@pytest.mark.usefixtures("_mock_constructors")
class TestCrewTasks:
    """Verifie que chaque methode @task retourne un objet."""

    def test_extraction_and_macro_filtering(self, crew_instance):
        assert crew_instance.extraction_and_macro_filtering() is not None

    def test_origin_identification_and_saas_qualification(self, crew_instance):
        assert crew_instance.origin_identification_and_saas_qualification() is not None

    def test_commercial_analysis(self, crew_instance):
        assert crew_instance.commercial_analysis() is not None

    def test_gamma_webpage_creation(self, crew_instance):
        assert crew_instance.gamma_webpage_creation() is not None

    def test_decision_makers_identification(self, crew_instance):
        assert crew_instance.decision_makers_identification() is not None

    def test_compile_final_company_analysis_report(self, crew_instance):
        assert crew_instance.compile_final_company_analysis_report() is not None


# ===========================================================================
# Tests du crew
# ===========================================================================


@pytest.mark.usefixtures("_mock_constructors")
class TestCrewMethod:
    """Verifie que la methode crew() retourne un objet."""

    def test_crew_returns_object(self, crew_instance):
        crew_instance.agents = [MagicMock()]
        crew_instance.tasks = [MagicMock()]
        assert crew_instance.crew() is not None

    def test_log_file_default_none(self, crew_instance):
        assert crew_instance.log_file is None

    def test_log_file_settable(self, crew_instance):
        crew_instance.log_file = "/tmp/test.json"
        assert crew_instance.log_file == "/tmp/test.json"
