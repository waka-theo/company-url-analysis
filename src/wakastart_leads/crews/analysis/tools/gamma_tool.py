"""Gamma API Tool for automated webpage creation from template."""

import os
import re
import time
import unicodedata

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

GAMMA_TEMPLATE_ID = "g_w56csm22x0u632h"
GAMMA_API_BASE = "https://public-api.gamma.app/v1.0"

# URLs publiques des images statiques (GitHub Raw)
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/waka-theo/company-url-analysis/refs/heads/main/public"
WAKASTELLAR_LOGO_URL = f"{GITHUB_RAW_BASE}/Logos-Wakstellar_Nom-full-blanc.png"
OPPORTUNITY_ANALYSIS_IMAGE_URL = (
    f"{GITHUB_RAW_BASE}/Gemini_Generated_Image_rzqb15rzqb15rzqb.png"
)

# APIs de resolution de logo entreprise
UNAVATAR_BASE = "https://unavatar.io"
GOOGLE_FAVICON_BASE = "https://www.google.com/s2/favicons?domain={domain}&sz=128"

# Proxy de transformation d'images (wsrv.nl - gratuit, sans cle API)
# Permet de redimensionner les logos pour harmoniser l'affichage dans Gamma
IMAGE_PROXY_BASE = "https://wsrv.nl"
LOGO_TARGET_WIDTH = 150
LOGO_TARGET_HEIGHT = 80


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
    company_name: str = Field(
        ...,
        description=(
            "Nom commercial de l'entreprise prospect. "
            "Utilise pour rechercher dynamiquement le logo de l'entreprise."
        ),
    )
    company_domain: str = Field(
        ...,
        description=(
            "Domaine du site web de l'entreprise (ex: 'wakastellar.com'). "
            "Utilise pour recuperer le logo via Clearbit Logo API. "
            "Ne pas inclure 'https://' ni 'www.', juste le domaine nu."
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

    def _resize_logo_via_proxy(self, original_url: str) -> str:
        """Redimensionne un logo via le proxy wsrv.nl pour harmoniser l'affichage."""
        from urllib.parse import quote

        # wsrv.nl params: w=width, h=height, fit=contain (garde proportions), output=png
        resized_url = (
            f"{IMAGE_PROXY_BASE}/?url={quote(original_url, safe='')}"
            f"&w={LOGO_TARGET_WIDTH}&h={LOGO_TARGET_HEIGHT}"
            f"&fit=contain&output=png"
        )
        return resized_url

    def _resolve_company_logo(self, domain: str, company_name: str) -> str:
        """Resout l'URL du logo de l'entreprise via Unavatar puis Google Favicon."""
        clean_domain = domain.strip().lower()
        clean_domain = clean_domain.replace("https://", "").replace("http://", "")
        clean_domain = clean_domain.replace("www.", "").rstrip("/")

        if not clean_domain:
            print(f"[GAMMA DEBUG] Domaine vide pour {company_name}, pas de logo")
            return ""

        original_logo_url: str | None = None

        # Strategie 1 : Unavatar (gratuit, sans cle API, agrege plusieurs sources)
        unavatar_url = f"{UNAVATAR_BASE}/{clean_domain}"
        try:
            response = requests.head(unavatar_url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"[GAMMA DEBUG] Logo Unavatar trouve pour {clean_domain}")
                original_logo_url = unavatar_url
        except requests.exceptions.RequestException as e:
            print(f"[GAMMA DEBUG] Unavatar erreur pour {clean_domain}: {e}")

        # Strategie 2 : Google Favicon (fallback)
        if not original_logo_url:
            original_logo_url = GOOGLE_FAVICON_BASE.format(domain=clean_domain)
            print(f"[GAMMA DEBUG] Fallback Google Favicon pour {clean_domain}")

        # Redimensionner via proxy pour harmoniser l'affichage (150x80px)
        resized_url = self._resize_logo_via_proxy(original_logo_url)
        print(f"[GAMMA DEBUG] Logo redimensionne: {LOGO_TARGET_WIDTH}x{LOGO_TARGET_HEIGHT}px")
        return resized_url

    def _build_enhanced_prompt(
        self,
        original_prompt: str,
        company_domain: str,
        company_name: str,
    ) -> str:
        """Construit le prompt enrichi avec les 3 images pour la premiere page."""
        company_logo_url = self._resolve_company_logo(company_domain, company_name)

        image_lines: list[str] = []

        if company_logo_url:
            image_lines.append(
                f"- A gauche, le logo de l'entreprise {company_name} : {company_logo_url}"
            )

        if OPPORTUNITY_ANALYSIS_IMAGE_URL:
            image_lines.append(
                f"- Au centre, l'image Opportunity Analysis : {OPPORTUNITY_ANALYSIS_IMAGE_URL}"
            )

        if WAKASTELLAR_LOGO_URL:
            image_lines.append(
                f"- A droite, le logo WakaStellar : {WAKASTELLAR_LOGO_URL}"
            )

        if not image_lines:
            return original_prompt

        # Construire l'URL du logo prospect
        company_logo_line = ""
        if company_logo_url:
            company_logo_line = (
                f"- GAUCHE : Logo {company_name} (redimensionner pour correspondre aux autres) : "
                f"{company_logo_url}\n"
            )

        image_section = (
            "\n\n"
            "=== LOGOS PREMIERE PAGE (TITLE CARD) ===\n"
            "Disposition : 3 logos alignes horizontalement, TOUS DE MEME HAUTEUR (environ 60-80px).\n"
            "Les logos doivent etre visuellement equilibres et harmonieux.\n\n"
            "Configuration precise :\n"
            f"{company_logo_line}"
            f"- CENTRE : Image 'Opportunity Analysis' (reference de taille) : {OPPORTUNITY_ANALYSIS_IMAGE_URL}\n"
            f"- DROITE : Logo WakaStellar (meme hauteur) : {WAKASTELLAR_LOGO_URL}\n\n"
            "IMPORTANT : Si le logo de gauche est trop grand ou a un fond blanc visible,\n"
            "le redimensionner et l'adapter pour qu'il s'integre harmonieusement avec les deux autres.\n"
            "Tous les logos doivent avoir une apparence professionnelle et coherente."
        )

        return original_prompt + image_section

    def _sanitize_slug(self, name: str) -> str:
        """Nettoie un nom pour en faire un slug URL-safe."""
        # Normaliser les accents
        slug = unicodedata.normalize("NFKD", name)
        slug = slug.encode("ascii", "ignore").decode("ascii")

        # Minuscules, remplacer espaces et caracteres speciaux par des tirets
        slug = slug.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")

        return slug or "prospect"

    def _get_linkener_token(self, api_base: str, username: str, password: str) -> str | None:
        """Obtient un access token Linkener."""
        try:
            response = requests.post(
                f"{api_base}/auth/new_token",
                json={"username": username, "password": password},
                timeout=10,
            )
            if response.status_code == 200:
                token = response.text.strip()
                return token if token else None
        except requests.exceptions.RequestException as e:
            print(f"[LINKENER DEBUG] Erreur authentification: {e}")
        return None

    def _create_linkener_url(self, gamma_url: str, company_name: str) -> str | None:
        """Cree un lien court Linkener pour l'URL Gamma."""
        api_base = os.getenv("LINKENER_API_BASE", "").strip()
        username = os.getenv("LINKENER_USERNAME", "").strip()
        password = os.getenv("LINKENER_PASSWORD", "").strip()

        if not all([api_base, username, password]):
            print("[LINKENER DEBUG] Variables d'environnement manquantes")
            return None

        # 1. Obtenir un access token
        token = self._get_linkener_token(api_base, username, password)
        if not token:
            return None

        # 2. Nettoyer le nom pour creer le slug
        slug = self._sanitize_slug(company_name)

        # 3. Creer le lien court
        try:
            response = requests.post(
                f"{api_base}/urls/",
                headers={"Authorization": token},
                json={"slug": slug, "url": gamma_url},
                timeout=30,
            )

            if response.status_code in (200, 201):
                # Construire l'URL finale (sans /api)
                base_url = api_base.replace("/api", "")
                return f"{base_url}/{slug}"

            # Gestion slug deja existant (409 Conflict)
            if response.status_code == 409:
                slug = f"{slug}-{int(time.time()) % 1000}"
                try:
                    retry_response = requests.post(
                        f"{api_base}/urls/",
                        headers={"Authorization": token},
                        json={"slug": slug, "url": gamma_url},
                        timeout=30,
                    )
                    if retry_response.status_code in (200, 201):
                        base_url = api_base.replace("/api", "")
                        return f"{base_url}/{slug}"
                except requests.exceptions.RequestException as e:
                    print(f"[LINKENER DEBUG] Erreur retry apres conflit: {e}")

        except requests.exceptions.RequestException as e:
            print(f"[LINKENER DEBUG] Erreur creation lien: {e}")

        return None

    def _run(self, prompt: str, company_name: str, company_domain: str) -> str:
        """Execute Gamma webpage creation from template."""
        api_key = os.getenv("GAMMA_API_KEY", "").strip()
        if not api_key:
            return "Erreur: GAMMA_API_KEY non configuree dans les variables d'environnement."

        # Construire le prompt enrichi avec les images
        enhanced_prompt = self._build_enhanced_prompt(prompt, company_domain, company_name)

        url = f"{GAMMA_API_BASE}/generations/from-template"

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": api_key,
        }

        payload = {
            "gammaId": GAMMA_TEMPLATE_ID,
            "prompt": enhanced_prompt,
            "sharingOptions": {
                "workspaceAccess": "view",
                "externalAccess": "view",
            },
        }

        print(f"[GAMMA DEBUG] Creation from template: {GAMMA_TEMPLATE_ID}")
        print(f"[GAMMA DEBUG] Cle API : {api_key[:8]}... (longueur: {len(api_key)})")
        print(f"[GAMMA DEBUG] Prompt enrichi (500 premiers chars): {enhanced_prompt[:500]}")

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

            gamma_url = self._poll_generation_status(generation_id, api_key)

            # Vérifier que c'est bien une URL valide
            if gamma_url.startswith("http"):
                # Créer le lien court automatiquement
                short_url = self._create_linkener_url(gamma_url, company_name)
                if short_url:
                    print(f"[GAMMA DEBUG] Lien court créé: {short_url}")
                    return short_url
                print("[GAMMA DEBUG] Linkener indisponible, retour URL Gamma")

            return gamma_url  # Fallback sur URL Gamma si Linkener échoue

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
