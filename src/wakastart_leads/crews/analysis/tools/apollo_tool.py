"""Apollo.io Search & Enrichment Tool pour l'identification des decideurs."""

import os
import re
from typing import ClassVar

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ApolloSearchInput(BaseModel):
    """Input schema pour ApolloSearchTool."""

    domain: str = Field(..., description="Domaine de l'entreprise (ex: stripe.com)")
    company_name: str = Field(..., description="Nom de l'entreprise pour contexte")


class ApolloSearchTool(BaseTool):
    """
    Recherche et enrichit les decideurs d'une entreprise via l'API Apollo.io.

    Etape 1 : People API Search (gratuit, 0 credit) pour trouver les decideurs par domaine.
    Etape 2 : People Enrichment (payant, 1 credit/appel) pour obtenir les coordonnees completes.

    Retourne jusqu'a 3 decideurs avec : nom, titre, email, telephone, LinkedIn.
    Priorise les C-Level (owner, founder, c_suite) puis VP/Head/Director.
    """

    name: str = "apollo_search"
    description: str = (
        "Recherche les decideurs d'une entreprise via Apollo.io. "
        "A partir du domaine (ex: stripe.com), retourne les contacts "
        "C-Level et Management avec leurs coordonnees professionnelles (email, LinkedIn). "
        "Utilise cet outil pour obtenir les decideurs d'une entreprise "
        "a partir de son site web."
    )
    args_schema: type[BaseModel] = ApolloSearchInput

    API_BASE: ClassVar[str] = "https://api.apollo.io/api/v1"
    SEARCH_ENDPOINT: ClassVar[str] = "/mixed_people/api_search"
    ENRICH_ENDPOINT: ClassVar[str] = "/people/match"

    # Priorite de tri par seniority (plus petit = plus prioritaire)
    SENIORITY_PRIORITY: ClassVar[dict[str, int]] = {
        "owner": 1,
        "founder": 2,
        "c_suite": 3,
        "vp": 4,
        "head": 5,
        "director": 6,
        "manager": 7,
    }

    # Seniorities ciblees pour la recherche
    TARGET_SENIORITIES: ClassVar[list[str]] = ["owner", "founder", "c_suite", "vp", "head", "director"]

    # Titres specifiques a cibler (CTO et variantes)
    TARGET_TITLES: ClassVar[list[str]] = ["CTO", "Chief Technology Officer", "Directeur Technique"]

    def _get_headers(self) -> dict[str, str]:
        """Construit les headers d'authentification Apollo."""
        api_key = os.getenv("APOLLO_API_KEY", "").strip()
        return {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

    def _build_search_params(self, domain: str, *, with_filters: bool = True) -> list[tuple[str, str]]:
        """Construit les query params pour People API Search.

        Args:
            domain: Domaine de l'entreprise.
            with_filters: Si True, ajoute les filtres seniority/titles/email_status.
                Si False, recherche par domaine seul (fallback pour petites entreprises).
        """
        params: list[tuple[str, str]] = []
        params.append(("q_organization_domains_list[]", domain))

        if with_filters:
            for s in self.TARGET_SENIORITIES:
                params.append(("person_seniorities[]", s))
            for t in self.TARGET_TITLES:
                params.append(("person_titles[]", t))
            params.append(("include_similar_titles", "true"))
            for status in ("verified", "likely to engage"):
                params.append(("contact_email_status[]", status))

        params.append(("per_page", "10"))
        params.append(("page", "1"))
        return params

    def _execute_search(self, params: list[tuple[str, str]]) -> list[dict]:
        """Execute un appel People API Search avec les params donnes.

        Raises:
            PermissionError: Cle API invalide ou endpoint inaccessible.
            ConnectionError: Rate limit ou erreur HTTP.
        """
        url = f"{self.API_BASE}{self.SEARCH_ENDPOINT}"
        response = requests.post(url, headers=self._get_headers(), params=params, timeout=30)

        if response.status_code == 401:
            raise PermissionError("Cle API Apollo invalide ou expiree.")
        if response.status_code == 403:
            raise PermissionError("Endpoint Apollo non accessible. Verifiez que vous utilisez une master API key.")
        if response.status_code == 429:
            raise ConnectionError("Limite de requetes Apollo atteinte (600/heure). Reessayez plus tard.")
        if response.status_code != 200:
            raise ConnectionError(f"Erreur API Apollo Search (code {response.status_code}): {response.text}")

        data = response.json()
        return data.get("people", [])

    def _search_people(self, domain: str) -> list[dict]:
        """
        Etape 1 : Recherche les decideurs d'un domaine via People API Search (gratuit).

        Strategie de fallback progressif :
        1. Recherche avec filtres (seniority + titles + email_status) pour les grandes entreprises.
        2. Si 0 resultats, fallback sans filtres (domaine seul) pour les petites entreprises
           dont les contacts n'ont pas de tags seniority dans Apollo.

        Les parametres Apollo avec suffix [] sont des query params (in: "query" dans l'OpenAPI spec).
        Ils doivent etre envoyes via params= et non json= pour etre interpretes correctement.

        Returns:
            Liste de candidats avec id, first_name, last_name_obfuscated, title, etc.
        """
        # Essai 1 : recherche filtree (seniority + titles + email_status)
        params = self._build_search_params(domain, with_filters=True)
        people = self._execute_search(params)

        if people:
            return people

        # Fallback : recherche par domaine seul (petites entreprises sans tags seniority)
        params_fallback = self._build_search_params(domain, with_filters=False)
        return self._execute_search(params_fallback)

    def _enrich_person(self, apollo_id: str) -> dict | None:
        """
        Etape 2 : Enrichit un decideur par son ID Apollo (payant, 1 credit).

        Returns:
            Dictionnaire avec les donnees completes du decideur, ou None si echec.
        """
        url = f"{self.API_BASE}{self.ENRICH_ENDPOINT}"
        payload = {
            "id": apollo_id,
            "reveal_personal_emails": True,
        }

        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=30)

            if response.status_code != 200:
                return None

            data = response.json()
            return data.get("person")

        except requests.exceptions.RequestException:
            return None

    def _rank_candidates(self, people: list[dict]) -> list[dict]:
        """Trie les candidats par seniority puis par disponibilite email."""
        if not people:
            return []

        def _seniority_from_title(title: str | None) -> int:
            """Infere une priorite depuis le titre quand la seniority n'est pas disponible."""
            if not title:
                return 99
            title_lower = title.lower()
            # Word boundary matching pour eviter les faux positifs (ex: "cto" dans "director")
            if re.search(r"\b(?:ceo|cto|coo|cfo|cio|chief)\b", title_lower):
                return self.SENIORITY_PRIORITY["c_suite"]
            if re.search(r"\b(?:founder|fondateur|co-founder)\b", title_lower):
                return self.SENIORITY_PRIORITY["founder"]
            if re.search(r"\b(?:owner|proprietaire)\b", title_lower):
                return self.SENIORITY_PRIORITY["owner"]
            if re.search(r"\b(?:vp|vice president)\b", title_lower):
                return self.SENIORITY_PRIORITY["vp"]
            if re.search(r"\bhead\b", title_lower):
                return self.SENIORITY_PRIORITY["head"]
            if re.search(r"\b(?:director|directeur|directrice)\b", title_lower):
                return self.SENIORITY_PRIORITY["director"]
            if re.search(r"\bmanager\b", title_lower):
                return self.SENIORITY_PRIORITY["manager"]
            return 99

        sorted_people = sorted(
            people,
            key=lambda p: (
                _seniority_from_title(p.get("title")),
                not p.get("has_email", False),
            ),
        )
        return sorted_people[:3]

    def _build_linkedin_url(self, url: str | None) -> str:
        """Normalise l'URL LinkedIn."""
        if not url:
            return "Non trouve"

        if "linkedin.com" in url:
            if url.startswith("http"):
                return url
            return f"https://www.{url}" if not url.startswith("www.") else f"https://{url}"

        # Si c'est juste un handle
        return f"https://www.linkedin.com/in/{url}"

    def _format_decideurs(self, enriched_people: list[dict], company_name: str) -> dict:
        """Formate les decideurs enrichis en structure compatible CSV."""
        empty_decideur = {
            "nom": "Non trouve",
            "titre": "Non trouve",
            "email": "Non trouve",
            "telephone": "Non trouve",
            "linkedin": "Non trouve",
        }

        decideurs = []
        for person in enriched_people[:3]:
            first_name = person.get("first_name") or ""
            last_name = person.get("last_name") or ""
            full_name = f"{first_name} {last_name}".strip() or "Non trouve"

            decideurs.append(
                {
                    "nom": full_name,
                    "titre": person.get("title") or "Non trouve",
                    "email": person.get("email") or "Non trouve",
                    "telephone": person.get("phone_number") or "Non trouve",
                    "linkedin": self._build_linkedin_url(person.get("linkedin_url")),
                }
            )

        # Completer a 3 decideurs
        while len(decideurs) < 3:
            decideurs.append(empty_decideur.copy())

        return {
            "company": company_name,
            "decideurs": decideurs,
            "contacts_found": len(enriched_people),
        }

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

    def _run(self, domain: str, company_name: str) -> str:
        """Execute la recherche et l'enrichissement Apollo."""
        api_key = os.getenv("APOLLO_API_KEY", "").strip()
        if not api_key:
            return "Erreur: APOLLO_API_KEY non configuree dans les variables d'environnement."

        try:
            # Etape 1 : Recherche gratuite des decideurs
            candidates = self._search_people(domain)

            if not candidates:
                return f"Aucun decideur trouve pour {company_name} ({domain})."

            # Tri par pertinence
            top_candidates = self._rank_candidates(candidates)

            # Etape 2 : Enrichissement des top 3 (payant)
            enriched_people = []
            for candidate in top_candidates:
                apollo_id = candidate.get("id")
                if not apollo_id:
                    continue

                person = self._enrich_person(apollo_id)
                if person:
                    enriched_people.append(person)

            if not enriched_people:
                return f"Decideurs trouves mais enrichissement echoue pour {company_name} ({domain})."

            result = self._format_decideurs(enriched_people, company_name)
            return self._format_output(result)

        except PermissionError as e:
            return f"Erreur: {e!s}"
        except ConnectionError as e:
            return f"Erreur: {e!s}"
        except requests.exceptions.Timeout:
            return "Erreur: Timeout lors de la connexion a l'API Apollo."
        except requests.exceptions.RequestException as e:
            return f"Erreur de connexion a l'API Apollo: {e!s}"
        except Exception as e:
            return f"Erreur inattendue: {e!s}"
