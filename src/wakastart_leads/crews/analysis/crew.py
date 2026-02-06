"""Analysis crew - Analyse complete des entreprises SaaS pour WakaStart."""

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

from wakastart_leads.shared.tools.sirene_tool import SireneSearchTool

from .tools.apollo_tool import ApolloSearchTool
from .tools.gamma_tool import GammaCreateTool


@CrewBase
class AnalysisCrew:
    """Analysis crew - Analyse complete des entreprises SaaS"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    log_file: str | None = None

    @agent
    def economic_intelligence_analyst(self) -> Agent:
        """ACT 0 + ACT 1 : Expert en Intelligence Economique & Tech Scouting"""
        return Agent(
            config=self.agents_config["economic_intelligence_analyst"],
            tools=[ScrapeWebsiteTool(), SerperDevTool(), SireneSearchTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gemini/gemini-2.5-flash",  # Optimise: extraction de donnees
                temperature=0.2,
            ),
        )

    @agent
    def corporate_analyst_and_saas_qualifier(self) -> Agent:
        """ACT 2 + ACT 3 : Analyste Donnees Corporatives & Qualification SaaS"""
        return Agent(
            config=self.agents_config["corporate_analyst_and_saas_qualifier"],
            tools=[SerperDevTool(), ScrapeWebsiteTool(), SireneSearchTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gemini/gemini-2.5-flash",  # Optimise: qualification SaaS
                temperature=0.4,
            ),
        )

    @agent
    def wakastart_sales_engineer(self) -> Agent:
        """ACT 4 : Ingenieur Commercial Senior WakaStart"""
        return Agent(
            config=self.agents_config["wakastart_sales_engineer"],
            tools=[ScrapeWebsiteTool(), SerperDevTool(), SireneSearchTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="anthropic/claude-sonnet-4-5-20250929",  # Premium: scoring commercial critique
                temperature=0.6,
            ),
        )

    @agent
    def gamma_webpage_creator(self) -> Agent:
        """Architecte de Contenu Commercial Digital - Creation pages Gamma"""
        return Agent(
            config=self.agents_config["gamma_webpage_creator"],
            tools=[GammaCreateTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gemini/gemini-2.5-pro",  # Premium: creation contenu commercial creatif
                temperature=0.3,
            ),
        )

    @agent
    def lead_generation_expert(self) -> Agent:
        """ACT 5 : Expert en Lead Generation & Profiling"""
        return Agent(
            config=self.agents_config["lead_generation_expert"],
            tools=[
                SerperDevTool(),
                ScrapeWebsiteTool(),
                SireneSearchTool(),
                ApolloSearchTool(),
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gemini/gemini-2.5-flash",  # Optimise: identification decideurs
                temperature=0.2,
            ),
        )

    @agent
    def data_compiler_and_reporter(self) -> Agent:
        """Data Compiler : Compilation CSV finale (23 colonnes)"""
        return Agent(
            config=self.agents_config["data_compiler_and_reporter"],
            tools=[],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gemini/gemini-2.0-flash-lite",  # Budget: formatage CSV simple
                temperature=0.1,
            ),
        )

    @task
    def extraction_and_macro_filtering(self) -> Task:
        """ACT 0 + ACT 1 : Extraction, nettoyage, filtrage macro et detection SaaS cache"""
        return Task(
            config=self.tasks_config["extraction_and_macro_filtering"],
            markdown=False,
        )

    @task
    def origin_identification_and_saas_qualification(self) -> Task:
        """ACT 2 + ACT 3 : Identification origine et qualification SaaS"""
        return Task(
            config=self.tasks_config["origin_identification_and_saas_qualification"],
            markdown=False,
        )

    @task
    def commercial_analysis(self) -> Task:
        """ACT 4 : Analyse commerciale et scoring WakaStart"""
        return Task(
            config=self.tasks_config["commercial_analysis"],
            markdown=False,
        )

    @task
    def gamma_webpage_creation(self) -> Task:
        """Creation de pages web Gamma pour chaque prospect"""
        return Task(
            config=self.tasks_config["gamma_webpage_creation"],
            markdown=False,
        )

    @task
    def decision_makers_identification(self) -> Task:
        """ACT 5 : Identification des decideurs (CEO, CTO, etc.)"""
        return Task(
            config=self.tasks_config["decision_makers_identification"],
            markdown=False,
        )

    @task
    def compile_final_company_analysis_report(self) -> Task:
        return Task(
            config=self.tasks_config["compile_final_company_analysis_report"],
            markdown=False,
            output_file="src/wakastart_leads/crews/analysis/output/company_report_new.csv",
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Analysis crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            chat_llm=LLM(model="gemini/gemini-2.0-flash-lite"),  # Optimise: chat interne
            output_log_file=self.log_file,
        )
