"""Zeliq Email Enrichment Tool pour l'enrichissement des emails via LinkedIn."""

import json
import os
import time
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

    Supporte deux modes :
    - Mode Pipedream (si ZELIQ_WEBHOOK_URL definie) : envoie a un endpoint fixe
    - Mode webhook.site (par defaut) : cree un webhook temporaire et poll le resultat
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

    def _get_webhook_url(self) -> tuple[str, str | None]:
        """
        Retourne l'URL du webhook a utiliser.

        Returns:
            tuple: (webhook_url, token_uuid ou None si mode Pipedream)
        """
        # Mode Pipedream : utiliser l'URL fixe configuree
        pipedream_url = os.getenv("ZELIQ_WEBHOOK_URL", "").strip()
        if pipedream_url:
            return pipedream_url, None

        # Mode webhook.site : creer un webhook temporaire
        return self._create_webhook_url()

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
    ) -> tuple[bool, str | None]:
        """
        Appelle l'API Zeliq.

        Returns:
            tuple: (success: bool, job_id: str ou None)
        """
        api_key = os.getenv("ZELIQ_API_KEY", "").strip()
        if not api_key:
            raise ValueError("ZELIQ_API_KEY non configuree dans les variables d'environnement.")

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "linkedin_url": linkedin_url,
            "callback_url": callback_url,
        }

        try:
            response = requests.post(
                self.ZELIQ_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code in (401, 400):
                return False, None

            # Zeliq retourne 200 ou 201 avec un jobId
            if response.status_code in (200, 201):
                try:
                    data = response.json()
                    job_id = data.get("jobId")
                    return True, job_id
                except json.JSONDecodeError:
                    return True, None

            return False, None

        except requests.exceptions.RequestException:
            return False, None

    def _poll_webhook(self, token_uuid: str) -> dict | None:
        """Poll webhook.site jusqu'a reception de la reponse Zeliq. Retourne les donnees ou None."""
        elapsed = 0
        while elapsed < self.POLL_TIMEOUT:
            try:
                response = requests.get(
                    f"{self.WEBHOOK_SITE_URL}/token/{token_uuid}/requests",
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    requests_list = data.get("data", [])

                    if requests_list:
                        # Prendre la premiere requete (la plus recente)
                        first_request = requests_list[0]
                        content = first_request.get("content", "{}")
                        return json.loads(content)

            except requests.exceptions.RequestException:
                return None
            except json.JSONDecodeError:
                return None

            time.sleep(self.POLL_INTERVAL)
            elapsed += self.POLL_INTERVAL

        return None

    def _poll_pipedream(self, linkedin_url: str) -> dict | None:
        """Poll Pipedream Data Store pour recuperer le resultat Zeliq. Retourne les donnees ou None."""
        retrieve_url = os.getenv("ZELIQ_RETRIEVE_URL", "").strip()
        if not retrieve_url:
            return None

        elapsed = 0
        while elapsed < self.POLL_TIMEOUT:
            try:
                response = requests.get(
                    retrieve_url,
                    params={"key": linkedin_url},
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("found") and data.get("data"):
                        result = data["data"]
                        # Si le resultat est une chaine JSON, la parser
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except json.JSONDecodeError:
                                pass
                        return result

            except requests.exceptions.RequestException:
                pass
            except json.JSONDecodeError:
                pass

            time.sleep(self.POLL_INTERVAL)
            elapsed += self.POLL_INTERVAL

        return None

    def _run(
        self,
        first_name: str,
        last_name: str,
        company: str,
        linkedin_url: str,
    ) -> str:
        """Execute l'enrichissement email via Zeliq."""
        full_name = f"{first_name} {last_name}"

        # Verifier la cle API
        api_key = os.getenv("ZELIQ_API_KEY", "").strip()
        if not api_key:
            return f"Erreur: ZELIQ_API_KEY non configuree. Impossible d'enrichir l'email de {full_name}."

        # Etape 1: Obtenir l'URL du webhook
        try:
            webhook_url, token_uuid = self._get_webhook_url()
        except RuntimeError as e:
            return f"Erreur lors de la creation du webhook pour {full_name}: {e!s}"

        # Mode Pipedream detecte
        is_pipedream_mode = token_uuid is None

        # Etape 2: Appeler l'API Zeliq
        success, job_id = self._call_zeliq_api(
            first_name=first_name,
            last_name=last_name,
            company=company,
            linkedin_url=linkedin_url,
            callback_url=webhook_url,
        )

        if not success:
            return f"Echec de l'appel API Zeliq pour {full_name}. Email non enrichi."

        # Mode Pipedream : poll le Data Store pour recuperer le resultat
        if is_pipedream_mode:
            result = self._poll_pipedream(linkedin_url)

            if result is None:
                return (
                    f"Enrichissement Zeliq lance pour {full_name} (job: {job_id or 'N/A'}). "
                    f"Timeout en attente de reponse. Utiliser l'email Hunter comme fallback."
                )

            # Extraire l'email du resultat Pipedream
            contact = result.get("contact", {})
            email = contact.get("most_probable_email")
            status = contact.get("most_probable_email_status", "unknown")

            if not email:
                return f"Aucun email trouve par Zeliq pour {full_name}."

            return f"Email enrichi pour {full_name}:\n- Email: {email}\n- Statut: {status}"

        # Mode webhook.site : poll pour recuperer le resultat
        result = self._poll_webhook(token_uuid)

        if result is None:
            return f"Timeout: Zeliq n'a pas repondu dans le delai imparti pour {full_name}. Email non enrichi."

        # Extraire l'email
        contact = result.get("contact", {})
        email = contact.get("most_probable_email")
        status = contact.get("most_probable_email_status", "unknown")

        if not email:
            return f"Aucun email trouve par Zeliq pour {full_name}."

        return f"Email enrichi pour {full_name}:\n- Email: {email}\n- Statut: {status}"
