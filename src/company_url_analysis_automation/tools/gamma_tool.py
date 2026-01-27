"""Gamma API Tool for automated webpage creation from template."""

import os
import time

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

GAMMA_TEMPLATE_ID = "g_w56csm22x0u632h"
GAMMA_API_BASE = "https://public-api.gamma.app/v1.0"


class GammaCreateInput(BaseModel):
    """Input schema for GammaCreateTool."""

    prompt: str = Field(
        ...,
        description=(
            "Prompt de personnalisation pour adapter le template Gamma au prospect. "
            "Doit contenir : nom de l'entreprise, secteur, problematiques identifiees, "
            "offres WakaStart pertinentes, et proposition de valeur personnalisee. "
            "Ce texte sera utilise par Gamma pour adapter le template de vente."
        ),
    )


class GammaCreateTool(BaseTool):
    """
    Outil pour creer une page web Gamma a partir du template de vente WakaStart.

    Utilise l'endpoint from-template pour cloner le template de reference
    et l'adapter au prospect via un prompt de personnalisation.
    Retourne l'URL de la page web creee.
    """

    name: str = "gamma_create_webpage"
    description: str = (
        "Cree une page web Gamma a partir du template de presentation commerciale WakaStart. "
        "Fournir un prompt de personnalisation contenant les donnees du prospect "
        "(nom, secteur, problematiques, offres WakaStart pertinentes). "
        "Le template est pre-defini et sera adapte automatiquement. "
        "Retourne l'URL de la page web creee."
    )
    args_schema: type[BaseModel] = GammaCreateInput

    def _run(self, prompt: str) -> str:
        """Execute Gamma webpage creation from template."""
        api_key = os.getenv("GAMMA_API_KEY", "").strip()
        if not api_key:
            return "Erreur: GAMMA_API_KEY non configuree dans les variables d'environnement."

        url = f"{GAMMA_API_BASE}/generations/from-template"

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }

        payload = {
            "gammaId": GAMMA_TEMPLATE_ID,
            "prompt": prompt,
            "sharingOptions": {
                "workspaceAccess": "view",
                "externalAccess": "view",
            },
        }

        print(f"[GAMMA DEBUG] Creation from template: {GAMMA_TEMPLATE_ID}")
        print(f"[GAMMA DEBUG] Cle API : {api_key[:8]}... (longueur: {len(api_key)})")
        print(f"[GAMMA DEBUG] Prompt (500 premiers chars): {prompt[:500]}")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)

            print(f"[GAMMA DEBUG] Status POST from-template: {response.status_code}")

            if response.status_code == 400:
                error_data = response.json()
                return f"Erreur Gamma (validation) : {error_data.get('message', response.text)}"
            elif response.status_code == 403:
                return "Erreur: Cle API Gamma invalide ou permissions insuffisantes."
            elif response.status_code == 429:
                return "Erreur: Limite de requetes Gamma atteinte. Reessayez plus tard."
            elif response.status_code not in (200, 201):
                print(f"[GAMMA DEBUG] Response body: {response.text[:500]}")
                return f"Erreur API Gamma (code {response.status_code}): {response.text}"

            data = response.json()
            generation_id = data.get("generationId")
            if not generation_id:
                print(f"[GAMMA DEBUG] Reponse POST sans generationId: {data}")
                return "Erreur: Reponse Gamma sans generationId."

            print(f"[GAMMA DEBUG] Generation ID: {generation_id}")
            print("[GAMMA DEBUG] Demarrage du polling...")

            return self._poll_generation_status(generation_id, api_key)

        except requests.exceptions.Timeout:
            return "Erreur: Timeout lors de la creation Gamma (120s)."
        except requests.exceptions.RequestException as e:
            return f"Erreur de connexion a l'API Gamma: {e!s}"
        except Exception as e:
            return f"Erreur inattendue Gamma: {e!s}"

    def _poll_generation_status(
        self,
        generation_id: str,
        api_key: str,
        poll_interval: int = 3,
        max_retries: int = 60,
    ) -> str:
        """Poll GET /v1.0/generations/{id} until completed, return gammaUrl."""
        url = f"{GAMMA_API_BASE}/generations/{generation_id}"
        headers = {
            "X-API-KEY": api_key,
            "Accept": "application/json",
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code != 200:
                    print(f"[GAMMA DEBUG] Poll attempt {attempt + 1}: HTTP {response.status_code}")
                    if response.status_code in (401, 403):
                        return f"Erreur: Authentification Gamma echouee lors du polling (HTTP {response.status_code})"
                    time.sleep(poll_interval)
                    continue

                data = response.json()
                status = data.get("status", "unknown")
                print(f"[GAMMA DEBUG] Poll attempt {attempt + 1}: status={status}")

                if status == "completed":
                    # Chercher l'URL dans les champs connus
                    for key in ("gammaUrl", "url", "link", "pageUrl", "docUrl"):
                        if data.get(key):
                            print(f"[GAMMA DEBUG] URL finale Gamma ({key}): {data[key]}")
                            return data[key]

                    # Log complet si aucun champ URL trouve
                    print(f"[GAMMA DEBUG] Reponse complete (aucun champ URL): {data}")
                    return f"Erreur: Generation terminee mais URL introuvable. Reponse: {data}"

                if status in ("failed", "error"):
                    error_msg = data.get("error", data.get("message", "Erreur inconnue"))
                    print(f"[GAMMA DEBUG] Generation echouee: {error_msg}")
                    return f"Erreur: Generation Gamma echouee: {error_msg}"

                # status == "pending" ou autre => continuer le polling
                time.sleep(poll_interval)

            except requests.exceptions.RequestException as e:
                print(f"[GAMMA DEBUG] Poll attempt {attempt + 1}: erreur reseau: {e}")
                time.sleep(poll_interval)

        return f"Erreur: Timeout polling Gamma apres {max_retries * poll_interval}s (generation_id={generation_id})"
