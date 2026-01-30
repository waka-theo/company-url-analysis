"""Enrichment crew for analyzing and scoring companies for WakaStart relevance."""

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool


@CrewBase
class EnrichmentCrew:
    """EnrichmentCrew - Enrichit les donnees d'entreprises avec nationalite, solution SaaS, pertinence et explication."""

    agents_config = "config/enrichment_agents.yaml"
    tasks_config = "config/enrichment_tasks.yaml"
    log_file: str | None = None

    @agent
    def saas_enrichment_analyst(self) -> Agent:
        """Agent d'analyse et qualification SaaS pour WakaStart"""
        return Agent(
            config=self.agents_config["saas_enrichment_analyst"],
            tools=[SerperDevTool(), ScrapeWebsiteTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=30,
            max_rpm=30,  # Limite pour éviter rate limiting API
            max_execution_time=None,
            llm=LLM(
                model="openai/gpt-4o",
                temperature=0.3,
            ),
        )

    @task
    def enrich_company_data(self) -> Task:
        """Tache d'enrichissement des donnees d'entreprises"""
        return Task(
            config=self.tasks_config["enrich_company_data"],
            markdown=False,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Enrichment crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            chat_llm=LLM(model="openai/gpt-4o-mini"),  # Modèle léger pour coordination interne
            output_log_file=self.log_file,
        )
