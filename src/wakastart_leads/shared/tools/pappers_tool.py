"""Pappers API Tool for French company data retrieval."""

import os

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class PappersSearchInput(BaseModel):
    """Input schema for PappersSearchTool."""

    query: str = Field(..., description="Nom de l'entreprise ou numéro SIREN à rechercher")


class PappersSearchTool(BaseTool):
    """
    Outil pour rechercher des entreprises françaises via l'API Pappers.

    Retourne les informations légales, les dirigeants et les données financières.
    """

    name: str = "pappers_search"
    description: str = (
        "Recherche une entreprise française par nom ou SIREN via l'API Pappers. "
        "Retourne les informations légales (SIREN, date de création, forme juridique), "
        "les dirigeants (noms, fonctions) et les données financières (CA, effectif). "
        "Utilise cet outil pour obtenir des données officielles sur les entreprises françaises."
    )
    args_schema: type[BaseModel] = PappersSearchInput

    def _run(self, query: str) -> str:
        """Execute Pappers search."""
        api_key = os.getenv("PAPPERS_API_KEY")
        if not api_key:
            return "Erreur: PAPPERS_API_KEY non configurée dans les variables d'environnement."

        base_url = "https://api.pappers.fr/v2"
        headers = {"api-key": api_key}

        # Déterminer si c'est un SIREN (9 chiffres) ou un nom
        clean_query = query.strip().replace(" ", "")
        is_siren = clean_query.isdigit() and len(clean_query) == 9

        try:
            if is_siren:
                # Recherche directe par SIREN
                response = requests.get(
                    f"{base_url}/entreprise", headers=headers, params={"siren": clean_query}, timeout=30
                )
            else:
                # Recherche par nom d'entreprise
                response = requests.get(
                    f"{base_url}/recherche",
                    headers=headers,
                    params={"q": query, "par_page": 5, "cibles": "nom_entreprise,denomination"},
                    timeout=30,
                )

            if response.status_code == 401:
                return "Erreur: Clé API Pappers invalide ou expirée."
            elif response.status_code == 404:
                return f"Aucune entreprise trouvée pour: {query}"
            elif response.status_code != 200:
                return f"Erreur API Pappers (code {response.status_code}): {response.text}"

            data = response.json()

            if is_siren:
                return self._format_company_details(data)
            else:
                return self._format_search_results(data, query)

        except requests.exceptions.Timeout:
            return "Erreur: Timeout lors de la connexion à l'API Pappers."
        except requests.exceptions.RequestException as e:
            return f"Erreur de connexion à l'API Pappers: {e!s}"
        except Exception as e:
            return f"Erreur inattendue: {e!s}"

    def _format_company_details(self, data: dict) -> str:
        """Format detailed company information."""
        result_parts = []

        # Informations de base
        nom = data.get("nom_entreprise") or data.get("denomination") or "Non disponible"
        result_parts.append(f"**Entreprise: {nom}**")
        result_parts.append(f"- SIREN: {data.get('siren', 'N/A')}")
        result_parts.append(f"- SIRET (siège): {data.get('siege', {}).get('siret', 'N/A')}")
        result_parts.append(f"- Forme juridique: {data.get('forme_juridique', 'N/A')}")
        result_parts.append(f"- Date de création: {data.get('date_creation', 'N/A')}")
        result_parts.append(f"- Date immatriculation RCS: {data.get('date_immatriculation_rcs', 'N/A')}")

        # Statut
        statut = "Active" if not data.get("entreprise_cessee") else "Cessée"
        result_parts.append(f"- Statut: {statut}")

        # Adresse du siège
        siege = data.get("siege", {})
        adresse = siege.get("adresse_ligne_1", "")
        code_postal = siege.get("code_postal", "")
        ville = siege.get("ville", "")
        if adresse or code_postal or ville:
            result_parts.append(f"- Adresse: {adresse}, {code_postal} {ville}".strip(", "))

        # Code NAF/APE
        result_parts.append(f"- Code NAF: {data.get('code_naf', 'N/A')} - {data.get('libelle_code_naf', '')}")

        # Données financières
        finances = data.get("finances", {})
        if finances:
            ca = finances.get("chiffre_affaires")
            resultat = finances.get("resultat")
            effectif = data.get("effectif")

            if ca:
                result_parts.append(f"- Chiffre d'affaires: {ca:,.0f} EUR".replace(",", " "))
            if resultat:
                result_parts.append(f"- Résultat: {resultat:,.0f} EUR".replace(",", " "))
            if effectif:
                result_parts.append(f"- Effectif: {effectif}")

        # Dirigeants
        representants = data.get("representants", [])
        if representants:
            result_parts.append("\n**Dirigeants:**")
            for rep in representants[:5]:  # Limiter à 5 dirigeants
                nom_complet = rep.get("nom_complet") or f"{rep.get('prenom', '')} {rep.get('nom', '')}".strip()
                qualite = rep.get("qualite", "Fonction non précisée")
                result_parts.append(f"- {nom_complet} ({qualite})")

        # Bénéficiaires effectifs
        beneficiaires = data.get("beneficiaires_effectifs", [])
        if beneficiaires:
            result_parts.append("\n**Bénéficiaires effectifs:**")
            for ben in beneficiaires[:3]:
                nom_complet = f"{ben.get('prenom', '')} {ben.get('nom', '')}".strip()
                pourcentage = ben.get("pourcentage_parts", "N/A")
                result_parts.append(f"- {nom_complet} ({pourcentage}% des parts)")

        return "\n".join(result_parts)

    def _format_search_results(self, data: dict, query: str) -> str:
        """Format search results."""
        results = []

        # Récupérer les résultats de différentes sources
        for key in ["resultats_nom_entreprise", "resultats_denomination", "resultats"]:
            if data.get(key):
                results.extend(data[key])

        if not results:
            return f"Aucune entreprise trouvée pour: {query}"

        result_parts = [f"**Résultats pour '{query}':**\n"]

        for i, entreprise in enumerate(results[:5], 1):
            nom = entreprise.get("nom_entreprise") or entreprise.get("denomination") or "Nom inconnu"
            siren = entreprise.get("siren", "N/A")
            ville = entreprise.get("siege", {}).get("ville", "") if entreprise.get("siege") else ""
            date_creation = entreprise.get("date_creation", "")

            result_parts.append(f"{i}. **{nom}**")
            result_parts.append(f"   - SIREN: {siren}")
            if ville:
                result_parts.append(f"   - Ville: {ville}")
            if date_creation:
                result_parts.append(f"   - Création: {date_creation}")
            result_parts.append("")

        result_parts.append("\n💡 Pour plus de détails, recherchez avec le numéro SIREN.")

        return "\n".join(result_parts)
