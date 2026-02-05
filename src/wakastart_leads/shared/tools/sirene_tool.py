"""Sirene INSEE API Tool for French company data retrieval."""

import os

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SireneSearchInput(BaseModel):
    """Input schema for SireneSearchTool."""

    query: str = Field(..., description="Nom de l'entreprise ou numero SIREN a rechercher")


class SireneSearchTool(BaseTool):
    """
    Outil pour rechercher des entreprises francaises via l'API Sirene de l'INSEE.

    Retourne les informations legales officielles : SIREN, SIRET, date de creation,
    forme juridique, adresse du siege et effectif.

    Configuration requise:
    - Creer un compte sur https://portail-api.insee.fr/
    - Creer une application (mode "simple", pas "backend to backend")
    - Souscrire a l'API Sirene (plan "Public")
    - Recuperer la cle API et la mettre dans INSEE_SIRENE_API_KEY
    """

    name: str = "sirene_search"
    description: str = (
        "Recherche une entreprise francaise par nom ou SIREN via l'API officielle Sirene de l'INSEE. "
        "Retourne les informations legales (SIREN, SIRET, date de creation, forme juridique), "
        "l'adresse du siege et la tranche d'effectif. "
        "Utilise cet outil pour obtenir des donnees officielles sur les entreprises francaises."
    )
    args_schema: type[BaseModel] = SireneSearchInput

    # URL officielle de l'API Sirene v3.11
    _BASE_URL: str = "https://api.insee.fr/api-sirene/3.11"

    def _get_headers(self) -> dict[str, str]:
        """Get API headers with authentication.

        La cle d'API se transmet dans le header X-INSEE-Api-Key-Integration.
        """
        api_key = os.getenv("INSEE_SIRENE_API_KEY")
        if not api_key:
            raise ValueError("INSEE_SIRENE_API_KEY non configuree dans les variables d'environnement")
        return {
            "X-INSEE-Api-Key-Integration": api_key,
            "Accept": "application/json",
        }

    def _run(self, query: str) -> str:
        """Execute Sirene search."""
        try:
            headers = self._get_headers()
        except ValueError as e:
            return f"Erreur: {e!s}"

        # Determiner si c'est un SIREN (9 chiffres) ou un nom
        clean_query = query.strip().replace(" ", "")
        is_siren = clean_query.isdigit() and len(clean_query) == 9

        try:
            if is_siren:
                return self._search_by_siren(clean_query, headers)
            else:
                return self._search_by_name(query, headers)

        except requests.exceptions.Timeout:
            return "Erreur: Timeout lors de la connexion a l'API Sirene INSEE."
        except requests.exceptions.RequestException as e:
            return f"Erreur de connexion a l'API Sirene: {e!s}"
        except Exception as e:
            return f"Erreur inattendue: {e!s}"

    def _search_by_siren(self, siren: str, headers: dict[str, str]) -> str:
        """Search company by SIREN number.

        Endpoint: GET /siren/{siren}
        Exemple: curl 'https://api.insee.fr/api-sirene/3.11/siren/309634954'
                 --header 'X-INSEE-Api-Key-Integration: xxxxx'
        """
        response = requests.get(f"{self._BASE_URL}/siren/{siren}", headers=headers, timeout=30)

        if response.status_code == 401:
            return "Erreur: Cle API Sirene INSEE invalide ou expiree."
        elif response.status_code == 404:
            return f"Aucune entreprise trouvee pour le SIREN: {siren}"
        elif response.status_code == 403:
            return "Erreur: Acces refuse. Verifiez votre souscription a l'API Sirene (plan Public)."
        elif response.status_code != 200:
            return f"Erreur API Sirene (code {response.status_code}): {response.text}"

        data = response.json()
        return self._format_unite_legale(data.get("uniteLegale", {}))

    def _search_by_name(self, name: str, headers: dict[str, str]) -> str:
        """Search company by name.

        Endpoint: GET /siren?q=...
        Recherche multicritere sur denominationUniteLegale.
        Syntaxe Sirene: champ:valeur* (wildcard en fin de mot)
        """
        # Nettoyer le nom pour la recherche (remplacer espaces par *)
        clean_name = name.strip().replace(" ", "*")
        search_query = f"periode(denominationUniteLegale:{clean_name}*)"

        response = requests.get(
            f"{self._BASE_URL}/siren",
            headers=headers,
            params={"q": search_query, "nombre": 5},
            timeout=30,
        )

        if response.status_code == 401:
            return "Erreur: Cle API Sirene INSEE invalide ou expiree."
        elif response.status_code == 404:
            return f"Aucune entreprise trouvee pour: {name}"
        elif response.status_code == 403:
            return "Erreur: Acces refuse. Verifiez votre souscription a l'API Sirene (plan Public)."
        elif response.status_code != 200:
            return f"Erreur API Sirene (code {response.status_code}): {response.text}"

        data = response.json()
        unites_legales = data.get("unitesLegales", [])

        if not unites_legales:
            return f"Aucune entreprise trouvee pour: {name}"

        return self._format_search_results(unites_legales, name)

    def _format_unite_legale(self, unite: dict) -> str:
        """Format detailed company information from uniteLegale."""
        result_parts = []

        # Periode courante (derniere periode non historisee)
        periodes = unite.get("periodesUniteLegale", [])
        periode_courante = periodes[0] if periodes else {}

        # Nom de l'entreprise
        nom = (
            periode_courante.get("denominationUniteLegale")
            or periode_courante.get("nomUniteLegale")
            or "Non disponible"
        )
        prenom = periode_courante.get("prenomUsuelUniteLegale", "")
        if prenom and not periode_courante.get("denominationUniteLegale"):
            nom = f"{prenom} {nom}"

        result_parts.append(f"**Entreprise: {nom}**")
        result_parts.append(f"- SIREN: {unite.get('siren', 'N/A')}")

        # Forme juridique
        categorie_juridique = periode_courante.get("categorieJuridiqueUniteLegale", "")
        if categorie_juridique:
            forme = self._get_forme_juridique(categorie_juridique)
            result_parts.append(f"- Forme juridique: {forme} ({categorie_juridique})")

        # Date de creation
        date_creation = unite.get("dateCreationUniteLegale", "N/A")
        result_parts.append(f"- Date de creation: {date_creation}")

        # Statut (actif ou cesse)
        etat = periode_courante.get("etatAdministratifUniteLegale", "")
        statut = "Active" if etat == "A" else "Cessée" if etat == "C" else "Inconnu"
        result_parts.append(f"- Statut: {statut}")

        # Activite principale (NAF)
        activite = periode_courante.get("activitePrincipaleUniteLegale", "")
        if activite:
            result_parts.append(f"- Code NAF: {activite}")

        # Tranche d'effectif
        tranche_effectif = unite.get("trancheEffectifsUniteLegale", "")
        if tranche_effectif:
            effectif = self._get_tranche_effectif(tranche_effectif)
            result_parts.append(f"- Effectif: {effectif}")

        # Categorie d'entreprise (PME, ETI, GE)
        categorie = unite.get("categorieEntreprise", "")
        if categorie:
            result_parts.append(f"- Categorie: {categorie}")

        result_parts.append("\nPour obtenir l'adresse du siege, utilisez l'endpoint /siret/{siret}.")

        return "\n".join(result_parts)

    def _format_search_results(self, unites: list, query: str) -> str:
        """Format search results."""
        if not unites:
            return f"Aucune entreprise trouvee pour: {query}"

        result_parts = [f"**Resultats pour '{query}':**\n"]

        for i, unite in enumerate(unites[:5], 1):
            periodes = unite.get("periodesUniteLegale", [])
            periode_courante = periodes[0] if periodes else {}

            nom = (
                periode_courante.get("denominationUniteLegale")
                or periode_courante.get("nomUniteLegale")
                or "Nom inconnu"
            )
            prenom = periode_courante.get("prenomUsuelUniteLegale", "")
            if prenom and not periode_courante.get("denominationUniteLegale"):
                nom = f"{prenom} {nom}"

            siren = unite.get("siren", "N/A")
            date_creation = unite.get("dateCreationUniteLegale", "")
            etat = periode_courante.get("etatAdministratifUniteLegale", "")
            statut = "Active" if etat == "A" else "Cessée" if etat == "C" else ""

            result_parts.append(f"{i}. **{nom}**")
            result_parts.append(f"   - SIREN: {siren}")
            if date_creation:
                result_parts.append(f"   - Creation: {date_creation}")
            if statut:
                result_parts.append(f"   - Statut: {statut}")
            result_parts.append("")

        result_parts.append("\nPour plus de details, recherchez avec le numero SIREN.")

        return "\n".join(result_parts)

    def _get_forme_juridique(self, code: str) -> str:
        """Convert legal form code to label."""
        formes = {
            "1000": "Entrepreneur individuel",
            "5499": "Société à responsabilité limitée (SARL)",
            "5510": "SARL unipersonnelle",
            "5720": "Société par actions simplifiée (SAS)",
            "5710": "SAS unipersonnelle (SASU)",
            "5599": "SA à conseil d'administration",
            "5699": "SA à directoire",
            "6540": "Société civile",
            "9220": "Association déclarée",
        }
        return formes.get(code, "Autre")

    def _get_tranche_effectif(self, code: str) -> str:
        """Convert workforce bracket code to label."""
        tranches = {
            "00": "0 salarié",
            "01": "1-2 salariés",
            "02": "3-5 salariés",
            "03": "6-9 salariés",
            "11": "10-19 salariés",
            "12": "20-49 salariés",
            "21": "50-99 salariés",
            "22": "100-199 salariés",
            "31": "200-249 salariés",
            "32": "250-499 salariés",
            "41": "500-999 salariés",
            "42": "1000-1999 salariés",
            "51": "2000-4999 salariés",
            "52": "5000-9999 salariés",
            "53": "10000+ salariés",
            "NN": "Non renseigné",
        }
        return tranches.get(code, f"Code {code}")
