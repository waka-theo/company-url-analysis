import os

from crewai import LLM
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import (
	ScrapeWebsiteTool,
	SerperDevTool
)





@CrewBase
class CompanyUrlAnalysisAutomationCrew:
    """CompanyUrlAnalysisAutomation crew"""

    
    @agent
    def url_validator_and_company_name_extractor(self) -> Agent:
        
        return Agent(
            config=self.agents_config["url_validator_and_company_name_extractor"],
            
            
            tools=[				ScrapeWebsiteTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            
            max_execution_time=None,
            llm=LLM(
                model="openai/gpt-4o-mini",
                temperature=0.3,
            ),

        )

    @agent
    def company_research_analyst(self) -> Agent:
        
        return Agent(
            config=self.agents_config["company_research_analyst"],
            
            
            tools=[				SerperDevTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            
            max_execution_time=None,
            llm=LLM(
                model="openai/gpt-4o",
                temperature=0.5,
            ),

        )

    @agent
    def data_compiler_and_reporter(self) -> Agent:
        
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
                model="openai/gpt-4o-mini",
                temperature=0.3,
            ),

        )



    @task
    def validate_urls_and_extract_company_names(self) -> Task:
        return Task(
            config=self.tasks_config["validate_urls_and_extract_company_names"],
            markdown=False,
            
            
        )
    
    @task
    def research_company_details(self) -> Task:
        return Task(
            config=self.tasks_config["research_company_details"],
            markdown=False,
            
            
        )
    
    @task
    def compile_final_company_analysis_report(self) -> Task:
        return Task(
            config=self.tasks_config["compile_final_company_analysis_report"],
            markdown=False,
            output_file="output/company_report.csv",
        )
    

    @crew
    def crew(self) -> Crew:
        """Creates the CompanyUrlAnalysisAutomation crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            chat_llm=LLM(model="openai/gpt-4o-mini"),
        )

    def _load_response_format(self, name):
        with open(os.path.join(self.base_directory, "config", f"{name}.json")) as f:
            json_schema = json.loads(f.read())

        return SchemaConverter.build(json_schema)
