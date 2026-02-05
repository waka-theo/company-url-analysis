"""Search crew for discovering SaaS company URLs from flexible search criteria."""

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

from wakastart_leads.shared.tools.sirene_tool import SireneSearchTool


@CrewBase
class SearchCrew:
    """SearchCrew - Decouvre des URLs d'entreprises SaaS a partir de criteres de recherche."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    log_file: str | None = None

    @agent
    def saas_discovery_scout(self) -> Agent:
        """Agent de decouverte et validation d'entreprises SaaS"""
        return Agent(
            config=self.agents_config["saas_discovery_scout"],
            tools=[SerperDevTool(), ScrapeWebsiteTool(), SireneSearchTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=40,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="anthropic/claude-sonnet-4-5-20250929",
                temperature=0.3,
            ),
        )

    @task
    def search_web_discovery(self) -> Task:
        """Phase 1 : Decouverte web via Serper"""
        return Task(
            config=self.tasks_config["search_web_discovery"],
            markdown=False,
        )

    @task
    def search_pappers_validation(self) -> Task:
        """Phase 2 : Validation legale via Pappers"""
        return Task(
            config=self.tasks_config["search_pappers_validation"],
            markdown=False,
        )

    @task
    def search_saas_deep_scan(self) -> Task:
        """Phase 3 : Verification SaaS approfondie et compilation finale"""
        return Task(
            config=self.tasks_config["search_saas_deep_scan"],
            markdown=False,
            output_file="src/wakastart_leads/crews/search/output/search_results_raw.json",
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Search crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            chat_llm=LLM(model="openai/gpt-4o-mini"),
            output_log_file=self.log_file,
        )
