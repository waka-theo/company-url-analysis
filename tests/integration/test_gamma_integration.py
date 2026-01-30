#!/usr/bin/env python
"""
Tests d'integration GammaCreateTool - Appels reels API Gamma.

Usage:
    python tests/integration/test_gamma_integration.py

Pre-requis:
    - Fichier .env avec GAMMA_API_KEY valide
    - Connexion internet active

ATTENTION: Ce script consomme des credits API Gamma reels.
"""

import io
import os
import sys
import time
import webbrowser
from contextlib import redirect_stdout
from pathlib import Path

# -- Resolution chemin projet et chargement .env --
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from wakastart_leads.crews.analysis.tools.gamma_tool import (
    UNAVATAR_BASE,
    GammaCreateTool,
)

# -- Couleurs ANSI --
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

results: list[tuple[str, str, bool]] = []
_gamma_url: str | None = None


def header(test_id: str, description: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"{BOLD}{CYAN}[{test_id}]{RESET} {description}")
    print(f"{'=' * 70}")


def report_pass(test_id: str, description: str, detail: str = "") -> None:
    results.append((test_id, description, True))
    msg = f"  {GREEN}PASS{RESET} - {description}"
    if detail:
        msg += f"\n       {detail}"
    print(msg)


def report_fail(test_id: str, description: str, detail: str = "") -> None:
    results.append((test_id, description, False))
    msg = f"  {RED}FAIL{RESET} - {description}"
    if detail:
        msg += f"\n       {detail}"
    print(msg)


def print_summary() -> None:
    print(f"\n{'=' * 70}")
    print(f"{BOLD}RESUME DES TESTS D'INTEGRATION GAMMA{RESET}")
    print(f"{'=' * 70}")
    passed = sum(1 for _, _, p in results if p)
    total = len(results)
    for test_id, desc, ok in results:
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {test_id} - {desc}")
    print(f"\n  Total : {passed}/{total} tests reussis")
    if passed == total:
        print(f"  {GREEN}{BOLD}Tous les tests sont passes !{RESET}")
    else:
        print(f"  {RED}{BOLD}{total - passed} test(s) echoue(s){RESET}")
    print()


# ============================================================
# Tests
# ============================================================


def test_2_3_6_missing_api_key() -> None:
    """Supprime GAMMA_API_KEY et verifie le message d'erreur explicite."""
    test_id = "2.3.6"
    desc = "Erreur explicite sans GAMMA_API_KEY"
    header(test_id, desc)

    original_key = os.environ.pop("GAMMA_API_KEY", None)

    try:
        tool = GammaCreateTool()
        result = tool._run(
            prompt="Test sans cle",
            company_name="TestCorp",
            company_domain="testcorp.com",
        )
        print(f"  Resultat : {result}")

        expected_msg = "GAMMA_API_KEY non configuree"
        if expected_msg in result:
            report_pass(test_id, desc, f"Message : {result}")
        else:
            report_fail(
                test_id, desc, f"Attendu contenant '{expected_msg}', obtenu : {result}"
            )
    finally:
        if original_key is not None:
            os.environ["GAMMA_API_KEY"] = original_key


def test_2_3_2_unavatar_logo_resolution() -> None:
    """Verifie que le logo est resolu via Unavatar pour google.com."""
    test_id = "2.3.2"
    desc = "Resolution logo via Unavatar (google.com)"
    header(test_id, desc)

    tool = GammaCreateTool()
    captured = io.StringIO()

    with redirect_stdout(captured):
        logo_url = tool._resolve_company_logo("google.com", "Google")

    output = captured.getvalue()
    print(f"  Logo URL : {logo_url}")
    print(f"  Logs captures :")
    for line in output.strip().splitlines():
        print(f"    {line}")

    unavatar_expected = f"{UNAVATAR_BASE}/google.com"
    checks_passed = True

    if logo_url == unavatar_expected:
        print(f"  {GREEN}OK{RESET} URL Unavatar correcte")
    else:
        print(f"  {RED}KO{RESET} Attendu : {unavatar_expected}, obtenu : {logo_url}")
        checks_passed = False

    if "Logo Unavatar trouve" in output:
        print(f"  {GREEN}OK{RESET} Log 'Logo Unavatar trouve' present")
    else:
        print(f"  {RED}KO{RESET} Log 'Logo Unavatar trouve' absent")
        checks_passed = False

    if checks_passed:
        report_pass(test_id, desc)
    else:
        report_fail(test_id, desc)


def test_2_3_3_google_fallback_logo() -> None:
    """Teste un domaine obscur -> fallback Google Favicon."""
    test_id = "2.3.3"
    desc = "Fallback Google Favicon (domaine obscur)"
    header(test_id, desc)

    tool = GammaCreateTool()
    obscure_domain = "xyzzy-unknown-domain-test-2024.fr"
    captured = io.StringIO()

    with redirect_stdout(captured):
        logo_url = tool._resolve_company_logo(obscure_domain, "TestObscure")

    output = captured.getvalue()
    print(f"  Domaine teste : {obscure_domain}")
    print(f"  Logo URL : {logo_url}")
    print(f"  Logs captures :")
    for line in output.strip().splitlines():
        print(f"    {line}")

    checks_passed = True

    if "google.com/s2/favicons" in logo_url:
        print(f"  {GREEN}OK{RESET} URL Google Favicon detectee")
    else:
        print(f"  {RED}KO{RESET} Attendu Google Favicon, obtenu : {logo_url}")
        checks_passed = False

    if "Fallback Google Favicon" in output:
        print(f"  {GREEN}OK{RESET} Log 'Fallback Google Favicon' present")
    else:
        print(f"  {RED}KO{RESET} Log 'Fallback Google Favicon' absent")
        checks_passed = False

    if checks_passed:
        report_pass(test_id, desc)
    else:
        report_fail(test_id, desc)


def test_2_3_1_full_page_creation() -> None:
    """Appel reel a GammaCreateTool._run -> attend une URL gamma.app valide."""
    global _gamma_url
    test_id = "2.3.1"
    desc = "Creation complete d'une page Gamma (France Care)"
    header(test_id, desc)

    tool = GammaCreateTool()
    print("  Appel de GammaCreateTool._run(...)")
    print("  Prompt  : 'Test France Care'")
    print("  Company : 'France Care'")
    print("  Domain  : 'https://www.france-care.fr/'")
    print(f"  {YELLOW}(Peut prendre 30s a 3 min selon l'API Gamma...){RESET}")
    print()

    start = time.time()
    result = tool._run(
        prompt="Test France Care",
        company_name="France Care",
        company_domain="https://www.france-care.fr/",
    )
    elapsed = time.time() - start

    print(f"\n  Resultat : {result}")
    print(f"  Duree   : {elapsed:.1f}s")

    if "https://gamma.app/" in result and "Erreur" not in result:
        report_pass(test_id, desc, f"URL : {result}")
        _gamma_url = result
    else:
        report_fail(test_id, desc, f"Resultat inattendu : {result}")


def _test_2_3_4_page_accessibility(gamma_url: str | None) -> None:
    """Ouvre l'URL Gamma dans le navigateur pour verification visuelle."""
    test_id = "2.3.4"
    desc = "Accessibilite publique de la page Gamma"
    header(test_id, desc)

    if gamma_url is None:
        report_fail(test_id, desc, "Skip : pas d'URL (test 2.3.1 echoue)")
        return

    print(f"  URL : {gamma_url}")
    print(f"  {YELLOW}Ouverture dans le navigateur...{RESET}")
    webbrowser.open(gamma_url)
    print()
    print(f"  {BOLD}VERIFICATION MANUELLE :{RESET}")
    print("  - La page doit s'afficher SANS demander de connexion")
    print("  - Le contenu doit etre visible publiquement")
    print("  - Aucun message 404 ou 'acces refuse'")
    print()

    user_input = (
        input("  La page est-elle accessible publiquement ? (o/n) : ").strip().lower()
    )
    if user_input in ("o", "oui", "y", "yes"):
        report_pass(test_id, desc)
    else:
        report_fail(test_id, desc, "Verification manuelle echouee")


def _test_2_3_5_three_images_first_page(gamma_url: str | None) -> None:
    """Verification visuelle des 3 images sur la premiere page."""
    test_id = "2.3.5"
    desc = "3 images premiere page (logo + Opportunity + WakaStellar)"
    header(test_id, desc)

    if gamma_url is None:
        report_fail(test_id, desc, "Skip : pas d'URL (test 2.3.1 echoue)")
        return

    print(f"  URL : {gamma_url}")
    print()
    print(f"  {BOLD}VERIFICATION MANUELLE :{RESET}")
    print(f"  Sur la PREMIERE PAGE (title card), verifier :")
    print(f"  1. {CYAN}Logo France Care{RESET} - a gauche")
    print(f"  2. {CYAN}Image Opportunity Analysis{RESET} - au centre")
    print(f"  3. {CYAN}Logo WakaStellar{RESET} (blanc) - a droite")
    print()
    print("  (le navigateur devrait deja etre ouvert depuis le test 2.3.4)")
    print()

    user_input = (
        input("  Les 3 images sont-elles presentes ? (o/n) : ").strip().lower()
    )
    if user_input in ("o", "oui", "y", "yes"):
        report_pass(test_id, desc)
    else:
        detail = input("  Que manque-t-il ? (Entree pour ignorer) : ").strip()
        report_fail(test_id, desc, detail or "Verification manuelle echouee")


# ============================================================
# Main
# ============================================================


def main() -> None:
    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  TESTS D'INTEGRATION - GammaCreateTool{RESET}")
    print(f"{BOLD}  Appels reels API Gamma / Clearbit / Google{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")

    # Pre-requis
    api_key = os.getenv("GAMMA_API_KEY", "").strip()
    if not api_key:
        print(f"\n  {RED}ERREUR : GAMMA_API_KEY non trouvee.{RESET}")
        print(f"  Verifiez votre fichier .env : {PROJECT_ROOT / '.env'}")
        sys.exit(1)

    print(f"\n  Cle API Gamma : {api_key[:8]}... ({len(api_key)} chars)")
    print(f"  Projet racine : {PROJECT_ROOT}")

    # 1. Tests rapides (pas d'appel Gamma)
    test_2_3_6_missing_api_key()
    test_2_3_2_unavatar_logo_resolution()
    test_2_3_3_google_fallback_logo()

    # 2. Test principal (appel API Gamma reel)
    test_2_3_1_full_page_creation()

    # 3. Tests visuels (interaction utilisateur)
    _test_2_3_4_page_accessibility(_gamma_url)
    _test_2_3_5_three_images_first_page(_gamma_url)

    # Resume
    print_summary()
    sys.exit(0 if all(p for _, _, p in results) else 1)


if __name__ == "__main__":
    main()
