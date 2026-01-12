# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CrewAI multi-agent system that analyzes company URLs. Given a list of URLs, it validates them, extracts company names, researches company details (nationality, founding year), and compiles a comprehensive report.

## Commands

```bash
# Install dependencies (creates .venv with Python 3.10)
crewai install

# Run the crew
crewai run

# Train the crew
crewai train <n_iterations> <output_filename>

# Test the crew
crewai test <n_iterations> <openai_model_name>

# Replay from a specific task
crewai replay <task_id>

# Add new dependencies
uv add <package-name>
```

## Architecture

### Agent Pipeline (Sequential)

1. **url_validator_and_company_name_extractor** - Validates URLs and extracts company names using `ScrapeWebsiteTool`
2. **company_research_analyst** - Researches nationality and founding year using `SerperDevTool`
3. **data_compiler_and_reporter** - Compiles findings into a markdown report

### Key Files

- `src/company_url_analysis_automation/crew.py` - Agent and task definitions with `@agent`, `@task`, `@crew` decorators
- `src/company_url_analysis_automation/config/agents.yaml` - Agent roles, goals, backstories
- `src/company_url_analysis_automation/config/tasks.yaml` - Task descriptions and expected outputs
- `src/company_url_analysis_automation/main.py` - Entry point, defines `inputs` dict with `urls` key

### Input Format

The crew expects an `inputs` dict with a `urls` key (see `main.py`). Modify the `urls` value to test with real URLs.

## Environment

Requires `.env` file with:
- `OPENAI_API_KEY` - Required for GPT-4o-mini (used by all agents)
- `SERPER_API_KEY` - Required for web search (company_research_analyst)

## LLM Configuration

All agents use `openai/gpt-4o-mini` with temperature 0.7. To change models, edit the `llm` parameter in each agent definition in `crew.py`.

But du projet : Je veux créer un système d'agent pour CrewAI, voici mon projet : à partir d'une liste d'url que je vais passer en input, je veux créer un crew qui va lister nom de l’entreprise à partir de l'url, vérifier que l'url est correcte, trouver la nationalité de l'entreprise et son année de création.
