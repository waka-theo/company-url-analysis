"""Hunter.io Domain Search Tool pour l'enrichissement des decideurs."""

import os
from typing import ClassVar

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
    SENIORITY_PRIORITY: ClassVar[dict[str, int]] = {"executive": 1, "senior": 2}

    def _build_linkedin_url(self, handle: str | None) -> str:
        """Construit l'URL LinkedIn complete a partir du handle."""
        if not handle:
            return "Non trouve"

        # Si c'est deja une URL complete ou partielle
        if "linkedin.com" in handle:
            if handle.startswith("http"):
                return handle
            return f"https://www.{handle}" if not handle.startswith("www.") else f"https://{handle}"

        # Sinon, c'est juste le handle
        return f"https://www.linkedin.com/in/{handle}"

    def _sort_contacts(self, contacts: list[dict]) -> list[dict]:
        """Trie les contacts par seniority (executive > senior) puis par confidence."""
        sorted_contacts = sorted(
            contacts,
            key=lambda c: (
                self.SENIORITY_PRIORITY.get(c.get("seniority"), 99),
                -c.get("confidence", 0),
            ),
        )
        return sorted_contacts[:3]

    def _format_decideurs(self, contacts: list[dict], company_name: str) -> dict:
        """Formate les contacts en structure de decideurs pour le CSV."""
        empty_decideur = {
            "nom": "Non trouve",
            "titre": "Non trouve",
            "email": "Non trouve",
            "telephone": "Non trouve",
            "linkedin": "Non trouve",
        }

        decideurs = []
        for contact in contacts[:3]:
            first_name = contact.get("first_name") or ""
            last_name = contact.get("last_name") or ""
            full_name = f"{first_name} {last_name}".strip() or "Non trouve"

            decideurs.append(
                {
                    "nom": full_name,
                    "titre": contact.get("position") or "Non trouve",
                    "email": contact.get("value") or "Non trouve",
                    "telephone": contact.get("phone_number") or "Non trouve",
                    "linkedin": self._build_linkedin_url(contact.get("linkedin")),
                }
            )

        # Completer a 3 decideurs
        while len(decideurs) < 3:
            decideurs.append(empty_decideur.copy())

        return {
            "company": company_name,
            "decideurs": decideurs,
            "contacts_found": len(contacts),
        }

    def _run(self, domain: str, company_name: str) -> str:
        """Execute Hunter Domain Search."""
        api_key = os.getenv("HUNTER_API_KEY", "").strip()
        if not api_key:
            return "Erreur: HUNTER_API_KEY non configuree dans les variables d'environnement."

        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "domain": domain,
            "api_key": api_key,
            "type": "personal",
            "seniority": "executive,senior",
            "department": "executive,management,it",
            "limit": 10,
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 401:
                return "Erreur: Cle API Hunter invalide ou expiree."
            elif response.status_code == 429:
                return "Erreur: Limite de requetes Hunter atteinte. Reessayez plus tard."
            elif response.status_code != 200:
                return f"Erreur API Hunter (code {response.status_code}): {response.text}"

            data = response.json()
            emails = data.get("data", {}).get("emails", [])

            if not emails:
                return f"Aucun decideur trouve pour {company_name} ({domain})."

            sorted_contacts = self._sort_contacts(emails)
            result = self._format_decideurs(sorted_contacts, company_name)

            return self._format_output(result)

        except requests.exceptions.Timeout:
            return "Erreur: Timeout lors de la connexion a l'API Hunter."
        except requests.exceptions.RequestException as e:
            return f"Erreur de connexion a l'API Hunter: {e!s}"
        except Exception as e:
            return f"Erreur inattendue: {e!s}"

    def _format_output(self, result: dict) -> str:
        """Formate le resultat en string lisible pour l'agent."""
        lines = [f"**Decideurs trouves pour {result['company']}** ({result['contacts_found']} contacts)"]
        lines.append("")

        for i, d in enumerate(result["decideurs"], 1):
            lines.append(f"**Decideur {i}:**")
            lines.append(f"- Nom: {d['nom']}")
            lines.append(f"- Titre: {d['titre']}")
            lines.append(f"- Email: {d['email']}")
            lines.append(f"- Telephone: {d['telephone']}")
            lines.append(f"- LinkedIn: {d['linkedin']}")
            lines.append("")

        return "\n".join(lines)
