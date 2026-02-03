"""Hunter.io Domain Search Tool pour l'enrichissement des decideurs."""

import os

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class HunterDomainSearchInput(BaseModel):
    """Input schema pour HunterDomainSearchTool."""

    domain: str = Field(..., description="Domaine de l'entreprise (ex: stripe.com)")
    company_name: str = Field(..., description="Nom de l'entreprise pour contexte")


class HunterDomainSearchTool(BaseTool):
    """
    Recherche les decideurs d'une entreprise via l'API Hunter.io Domain Search.

    A partir du domaine de l'entreprise, retourne jusqu'a 3 decideurs
    avec : nom, prenom, poste, email, telephone, LinkedIn.
    Priorise les C-Level (executive) puis le Management (senior).
    """

    name: str = "hunter_domain_search"
    description: str = (
        "Recherche les decideurs d'une entreprise via Hunter.io. "
        "A partir du domaine (ex: stripe.com), retourne les contacts "
        "C-Level et Management avec leurs coordonnees professionnelles. "
        "Utilise cet outil pour obtenir les decideurs d'une entreprise "
        "a partir de son site web."
    )
    args_schema: type[BaseModel] = HunterDomainSearchInput

    # Priorite de tri par seniority (plus petit = plus prioritaire)
    SENIORITY_PRIORITY: dict[str, int] = {"executive": 1, "senior": 2}

    def _run(self, domain: str, company_name: str) -> str:
        """Execute Hunter Domain Search."""
        # TODO: implementer dans Task 3
        return "Not implemented"
