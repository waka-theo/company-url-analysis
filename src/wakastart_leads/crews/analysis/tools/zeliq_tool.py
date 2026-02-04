"""Zeliq Email Enrichment Tool pour l'enrichissement des emails via LinkedIn."""

import os
from typing import ClassVar

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ZeliqEmailEnrichInput(BaseModel):
    """Input schema pour ZeliqEmailEnrichTool."""

    first_name: str = Field(..., description="Prenom du decideur")
    last_name: str = Field(..., description="Nom du decideur")
    company: str = Field(..., description="Nom ou domaine de l'entreprise")
    linkedin_url: str = Field(..., description="URL LinkedIn complete du decideur")


class ZeliqEmailEnrichTool(BaseTool):
    """
    Enrichit l'email d'un decideur via l'API Zeliq.

    A partir des informations du decideur (nom, prenom, entreprise, LinkedIn),
    retourne l'email le plus probable avec son statut de verification.
    Utilise webhook.site pour gerer l'API asynchrone de Zeliq.
    """

    name: str = "zeliq_email_enrich"
    description: str = (
        "Enrichit l'email d'un decideur via Zeliq. "
        "A partir du prenom, nom, entreprise et URL LinkedIn, "
        "retourne l'email professionnel le plus probable. "
        "Utilise cet outil apres Hunter pour obtenir des emails plus fiables."
    )
    args_schema: type[BaseModel] = ZeliqEmailEnrichInput

    # Configuration
    ZELIQ_API_URL: ClassVar[str] = "https://api.zeliq.com/api/contact/enrich/email"
    WEBHOOK_SITE_URL: ClassVar[str] = "https://webhook.site"
    POLL_INTERVAL: ClassVar[int] = 3  # secondes
    POLL_TIMEOUT: ClassVar[int] = 30  # secondes max

    def _create_webhook_url(self) -> tuple[str, str]:
        """Cree une URL unique via webhook.site. Retourne (webhook_url, token_uuid)."""
        try:
            response = requests.post(
                f"{self.WEBHOOK_SITE_URL}/token",
                timeout=10,
            )

            if response.status_code != 201:
                raise RuntimeError(
                    f"Erreur webhook.site (code {response.status_code}): impossible de creer le token"
                )

            data = response.json()
            token_uuid = data["uuid"]
            webhook_url = f"{self.WEBHOOK_SITE_URL}/{token_uuid}"

            return webhook_url, token_uuid

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erreur de connexion a webhook.site: {e!s}") from e

    def _call_zeliq_api(
        self,
        first_name: str,
        last_name: str,
        company: str,
        linkedin_url: str,
        callback_url: str,
    ) -> bool:
        """Appelle l'API Zeliq. Retourne True si l'appel a reussi."""
        raise NotImplementedError("A implementer dans Task 4")

    def _poll_webhook(self, token_uuid: str) -> dict | None:
        """Poll webhook.site jusqu'a reception de la reponse Zeliq. Retourne les donnees ou None."""
        raise NotImplementedError("A implementer dans Task 5")

    def _run(
        self,
        first_name: str,
        last_name: str,
        company: str,
        linkedin_url: str,
    ) -> str:
        """Execute l'enrichissement email via Zeliq."""
        raise NotImplementedError("A implementer dans Task 6")
