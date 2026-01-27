"""Kaspr API Tool for contact enrichment (email, phone)."""

import os
import re

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class KasprEnrichInput(BaseModel):
    """Input schema for KasprEnrichTool."""

    linkedin_url: str = Field(
        ..., description="URL du profil LinkedIn de la personne à enrichir (format: https://www.linkedin.com/in/xxx)"
    )
    full_name: str = Field(..., description="Nom complet de la personne (Prénom Nom)")


class KasprEnrichTool(BaseTool):
    """
    Outil pour enrichir les informations de contact via l'API Kaspr.

    À partir d'une URL LinkedIn et d'un nom, retourne l'email et le téléphone professionnels.
    """

    name: str = "kaspr_enrich"
    description: str = (
        "Enrichit les coordonnées d'un contact professionnel via l'API Kaspr. "
        "À partir de l'URL LinkedIn et du nom complet d'une personne, "
        "retourne son email professionnel et son numéro de téléphone. "
        "IMPORTANT: Nécessite une URL LinkedIn standard (pas SalesNavigator). "
        "Utilise cet outil pour obtenir les coordonnées vérifiées des décideurs."
    )
    args_schema: type[BaseModel] = KasprEnrichInput

    def _run(self, linkedin_url: str, full_name: str) -> str:
        """Execute Kaspr contact enrichment."""
        api_key = os.getenv("KASPR_API_KEY", "").strip()
        if not api_key:
            return "Erreur: KASPR_API_KEY non configurée dans les variables d'environnement."

        # Extraire l'ID LinkedIn de l'URL
        linkedin_id = self._extract_linkedin_id(linkedin_url)
        if not linkedin_id:
            return (
                f"Erreur: URL LinkedIn invalide: {linkedin_url}. Format attendu: https://www.linkedin.com/in/username"
            )

        url = "https://api.developers.kaspr.io/profile/linkedin"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "accept-version": "v2.0",
        }

        payload = {"id": linkedin_id, "name": full_name, "dataToGet": ["phone", "workEmail", "directEmail"]}

        print(f"[KASPR DEBUG] Clé API: {api_key[:8]}... (longueur: {len(api_key)})")
        print(f"[KASPR DEBUG] Payload: {payload}")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            print(f"[KASPR DEBUG] Status: {response.status_code}")

            if response.status_code == 401:
                print(f"[KASPR DEBUG] Response body: {response.text[:500]}")
                return "Erreur: Clé API Kaspr invalide ou expirée."
            elif response.status_code == 402:
                print(f"[KASPR DEBUG] Response body: {response.text[:500]}")
                return "Erreur: Crédits Kaspr insuffisants."
            elif response.status_code == 404:
                return f"Aucun contact trouvé pour: {full_name} ({linkedin_url})"
            elif response.status_code == 429:
                return "Erreur: Limite de requêtes Kaspr atteinte. Réessayez plus tard."
            elif response.status_code != 200:
                print(f"[KASPR DEBUG] Response body: {response.text[:500]}")
                return f"Erreur API Kaspr (code {response.status_code}): {response.text}"

            data = response.json()
            print(f"[KASPR DEBUG] Réponse brute pour {full_name}: {data}")
            return self._format_contact_info(data, full_name, linkedin_url)

        except requests.exceptions.Timeout:
            return "Erreur: Timeout lors de la connexion à l'API Kaspr."
        except requests.exceptions.RequestException as e:
            return f"Erreur de connexion à l'API Kaspr: {e!s}"
        except Exception as e:
            return f"Erreur inattendue: {e!s}"

    def _extract_linkedin_id(self, url: str) -> str | None:
        """Extract LinkedIn ID from URL."""
        # Patterns pour extraire l'ID LinkedIn
        patterns = [
            r"linkedin\.com/in/([^/?]+)",
            r"linkedin\.com/pub/([^/?]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1).strip("/")

        return None

    def _format_contact_info(self, data: dict, name: str, linkedin_url: str) -> str:
        """Format contact information from Kaspr response."""
        profile = data.get("profile", data)

        result_parts = [f"**Contact: {name}**"]
        result_parts.append(f"- LinkedIn: {linkedin_url}")

        # Emails professionnels (structure: professionalEmails[], starryProfessionalEmail)
        pro_emails = profile.get("professionalEmails", [])
        starry_pro = profile.get("starryProfessionalEmail")
        if pro_emails:
            result_parts.append(f"- Email professionnel: {pro_emails[0]}")
        elif starry_pro:
            result_parts.append(f"- Email professionnel: {starry_pro}")

        # Emails personnels (structure: personalEmails[], starryPersonalEmail)
        perso_emails = profile.get("personalEmails", [])
        starry_perso = profile.get("starryPersonalEmail")
        if perso_emails:
            result_parts.append(f"- Email personnel: {perso_emails[0]}")
        elif starry_perso:
            result_parts.append(f"- Email personnel: {starry_perso}")

        if not pro_emails and not starry_pro and not perso_emails and not starry_perso:
            result_parts.append("- Email: Non trouvé")

        # Téléphones (structure: phones[], starryPhone)
        phones = profile.get("phones", [])
        starry_phone = profile.get("starryPhone")
        if phones:
            result_parts.append(f"- Téléphone: {phones[0]}")
        elif starry_phone:
            result_parts.append(f"- Téléphone: {starry_phone}")
        else:
            result_parts.append("- Téléphone: Non trouvé")

        # Informations supplémentaires
        title = profile.get("title")
        company = profile.get("company")
        company_name = company.get("name") if isinstance(company, dict) else None

        if title:
            result_parts.append(f"- Poste: {title}")
        if company_name:
            result_parts.append(f"- Entreprise: {company_name}")

        return "\n".join(result_parts)
