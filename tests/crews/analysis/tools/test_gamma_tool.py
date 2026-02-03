"""Tests unitaires pour GammaCreateTool."""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests
from pydantic import ValidationError

from wakastart_leads.crews.analysis.tools.gamma_tool import (
    GAMMA_TEMPLATE_ID,
    OPPORTUNITY_ANALYSIS_IMAGE_URL,
    UNAVATAR_BASE,
    WAKASTELLAR_LOGO_URL,
    GammaCreateInput,
    GammaCreateTool,
)

# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestGammaToolInstantiation:
    def test_tool_name(self, gamma_tool):
        assert gamma_tool.name == "gamma_create_webpage"

    def test_tool_args_schema(self, gamma_tool):
        assert gamma_tool.args_schema is GammaCreateInput


# ===========================================================================
# Tests GammaCreateInput schema
# ===========================================================================


class TestGammaCreateInput:
    def test_all_fields_required(self):
        input_data = GammaCreateInput(
            prompt="Test prompt",
            company_name="TestCorp",
            company_domain="testcorp.com",
        )
        assert input_data.prompt == "Test prompt"
        assert input_data.company_name == "TestCorp"
        assert input_data.company_domain == "testcorp.com"

    def test_missing_company_name_raises(self):
        with pytest.raises(ValidationError):
            GammaCreateInput(prompt="Test", company_domain="test.com")

    def test_missing_company_domain_raises(self):
        with pytest.raises(ValidationError):
            GammaCreateInput(prompt="Test", company_name="Test")


# ===========================================================================
# Tests _resolve_company_logo
# ===========================================================================


class TestResolveCompanyLogo:
    PATCH_HEAD = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.head"

    def test_unavatar_success(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._resolve_company_logo("wakastellar.com", "WakaStellar")
            # Le resultat est maintenant encapsule dans wsrv.nl pour redimensionnement
            assert "wsrv.nl" in result
            assert "unavatar.io%2Fwakastellar.com" in result  # URL-encoded

    def test_unavatar_404_falls_back_to_google(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._resolve_company_logo("unknown.xyz", "Unknown")
            # Le resultat est encapsule dans wsrv.nl, contenant le fallback Google Favicon
            assert "wsrv.nl" in result
            assert "google.com" in result or "favicons" in result
            assert "unknown.xyz" in result

    def test_unavatar_timeout_falls_back_to_google(self, gamma_tool):
        with patch(self.PATCH_HEAD, side_effect=requests.exceptions.Timeout):
            result = gamma_tool._resolve_company_logo("slow.com", "Slow")
            # Le resultat est encapsule dans wsrv.nl, contenant le fallback Google Favicon
            assert "wsrv.nl" in result
            assert "google.com" in result or "favicons" in result

    def test_empty_domain_returns_empty(self, gamma_tool):
        result = gamma_tool._resolve_company_logo("", "TestCorp")
        assert result == ""

    def test_cleans_https_prefix(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp) as mock_head:
            gamma_tool._resolve_company_logo("https://www.testcorp.com/", "TestCorp")
            call_url = mock_head.call_args[0][0]
            assert call_url == f"{UNAVATAR_BASE}/testcorp.com"

    def test_cleans_http_prefix(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp) as mock_head:
            gamma_tool._resolve_company_logo("http://testcorp.com", "TestCorp")
            call_url = mock_head.call_args[0][0]
            assert call_url == f"{UNAVATAR_BASE}/testcorp.com"

    def test_cleans_trailing_slash(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp) as mock_head:
            gamma_tool._resolve_company_logo("testcorp.com/", "TestCorp")
            call_url = mock_head.call_args[0][0]
            assert call_url == f"{UNAVATAR_BASE}/testcorp.com"


# ===========================================================================
# Tests _build_enhanced_prompt
# ===========================================================================


class TestBuildEnhancedPrompt:
    PATCH_HEAD = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.head"

    def test_includes_all_three_images(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._build_enhanced_prompt("Base prompt", "testcorp.com", "TestCorp")
            assert "Base prompt" in result
            # Le logo entreprise est encapsule dans wsrv.nl pour redimensionnement
            assert "wsrv.nl" in result
            assert "unavatar.io%2Ftestcorp.com" in result  # URL-encoded dans wsrv.nl
            assert OPPORTUNITY_ANALYSIS_IMAGE_URL in result
            assert WAKASTELLAR_LOGO_URL in result

    def test_includes_placement_instructions(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._build_enhanced_prompt("Base prompt", "testcorp.com", "TestCorp")
            assert "LOGOS PREMIERE PAGE" in result
            assert "GAUCHE" in result
            assert "CENTRE" in result
            assert "DROITE" in result

    def test_empty_domain_omits_company_logo(self, gamma_tool):
        result = gamma_tool._build_enhanced_prompt("Base prompt", "", "TestCorp")
        assert UNAVATAR_BASE not in result
        assert "A gauche" not in result
        # Les deux autres images doivent toujours etre presentes
        assert OPPORTUNITY_ANALYSIS_IMAGE_URL in result
        assert WAKASTELLAR_LOGO_URL in result

    def test_preserves_original_prompt(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            original = "Mon prompt original avec du contenu important"
            result = gamma_tool._build_enhanced_prompt(original, "test.com", "Test")
            assert result.startswith(original)

    def test_includes_sizing_instructions(self, gamma_tool):
        """Le prompt doit contenir des instructions explicites de dimensionnement."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._build_enhanced_prompt("Base prompt", "testcorp.com", "TestCorp")
            # Nouvelles instructions attendues
            assert "LOGOS PREMIERE PAGE" in result or "LOGOS" in result
            assert "60-80px" in result or "meme hauteur" in result.lower()
            assert "redimensionner" in result.lower()


# ===========================================================================
# Tests _run
# ===========================================================================


class TestGammaRun:
    PATCH_POST = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.post"
    PATCH_GET = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.get"
    PATCH_HEAD = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.head"
    PATCH_SLEEP = "wakastart_leads.crews.analysis.tools.gamma_tool.time.sleep"
    SAMPLE_PROMPT = "WakaStellar - SaaS B2B - Migration legacy"
    SAMPLE_NAME = "TestCorp"
    SAMPLE_DOMAIN = "testcorp.com"

    def _mock_head_success(self):
        """Retourne un mock HEAD Unavatar reussi."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        return mock_resp

    def test_missing_api_key(self, gamma_tool, clear_all_api_keys):
        result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
        assert "GAMMA_API_KEY non configuree" in result

    def test_success_calls_poll(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(200, {"generationId": "gen123"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response),
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
            patch(self.PATCH_SLEEP),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "https://gamma.app/docs/abc123" in result

    def test_http_400(self, gamma_tool, mock_gamma_api_key, mock_response):
        resp = mock_response(400, {"message": "Invalid prompt"}, text="Bad Request")
        with (
            patch(self.PATCH_POST, return_value=resp),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "validation" in result.lower() or "Invalid prompt" in result

    def test_http_403(self, gamma_tool, mock_gamma_api_key, mock_response):
        with (
            patch(self.PATCH_POST, return_value=mock_response(403, text="Forbidden")),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "invalide" in result.lower() or "permissions" in result.lower()

    def test_http_429(self, gamma_tool, mock_gamma_api_key, mock_response):
        with (
            patch(self.PATCH_POST, return_value=mock_response(429)),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "Limite" in result or "requetes" in result

    def test_http_500(self, gamma_tool, mock_gamma_api_key, mock_response):
        with (
            patch(self.PATCH_POST, return_value=mock_response(500, text="Server error")),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "code 500" in result

    def test_no_generation_id(self, gamma_tool, mock_gamma_api_key, mock_response):
        with (
            patch(self.PATCH_POST, return_value=mock_response(200, {})),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "sans generationId" in result

    def test_timeout(self, gamma_tool, mock_gamma_api_key):
        with (
            patch(self.PATCH_POST, side_effect=requests.exceptions.Timeout),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "Timeout" in result
            assert "120s" in result

    def test_status_201(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(201, {"generationId": "gen201"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response),
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
            patch(self.PATCH_SLEEP),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "gamma.app" in result

    def test_correct_payload_uses_enhanced_prompt(
        self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status
    ):
        post_response = mock_response(200, {"generationId": "gen_payload"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response) as mock_post,
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
            patch(self.PATCH_SLEEP),
        ):
            gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            # Utiliser call_args_list[0] pour le premier POST (Gamma), pas le dernier (Linkener)
            first_call = mock_post.call_args_list[0]
            payload = first_call.kwargs.get("json") or first_call[1].get("json")
            assert payload["gammaId"] == GAMMA_TEMPLATE_ID
            # Le prompt doit etre enrichi (contient le prompt original + les logos)
            assert self.SAMPLE_PROMPT in payload["prompt"]
            assert "LOGOS PREMIERE PAGE" in payload["prompt"]
            assert WAKASTELLAR_LOGO_URL in payload["prompt"]
            assert payload["sharingOptions"]["workspaceAccess"] == "view"
            assert payload["sharingOptions"]["externalAccess"] == "view"

    def test_uses_template_id(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(200, {"generationId": "gen_tpl"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response) as mock_post,
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
            patch(self.PATCH_SLEEP),
        ):
            gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            # Utiliser call_args_list[0] pour le premier POST (Gamma), pas le dernier (Linkener)
            first_call = mock_post.call_args_list[0]
            payload = first_call.kwargs.get("json") or first_call[1].get("json")
            assert payload["gammaId"] == "g_w56csm22x0u632h"

    @patch.dict(
        os.environ,
        {
            "GAMMA_API_KEY": "test-key",
            "LINKENER_API_BASE": "https://url.wakastart.com/api",
            "LINKENER_USERNAME": "testuser",
            "LINKENER_PASSWORD": "testpass",
        },
    )
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.get")
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.head")
    def test_returns_linkener_url_when_available(self, mock_head, mock_get, mock_post):
        """Retourne l'URL Linkener si la creation reussit."""
        # Mock HEAD pour le logo
        mock_head.return_value = MagicMock(status_code=200)

        # Mock POST pour Gamma generation
        mock_gamma_gen = MagicMock()
        mock_gamma_gen.status_code = 200
        mock_gamma_gen.json.return_value = {"generationId": "gen123"}

        # Mock POST pour Linkener auth
        mock_linkener_auth = MagicMock()
        mock_linkener_auth.status_code = 200
        mock_linkener_auth.text = "test_token"

        # Mock POST pour Linkener create URL
        mock_linkener_create = MagicMock()
        mock_linkener_create.status_code = 201

        mock_post.side_effect = [mock_gamma_gen, mock_linkener_auth, mock_linkener_create]

        # Mock GET pour polling status (gammaUrl au premier niveau)
        mock_status = MagicMock()
        mock_status.status_code = 200
        mock_status.json.return_value = {"status": "completed", "gammaUrl": "https://gamma.app/docs/test123"}
        mock_get.return_value = mock_status

        tool = GammaCreateTool()
        result = tool._run("Test prompt", "TestCorp", "testcorp.com")

        assert result == "https://url.wakastart.com/testcorp"


# ===========================================================================
# Tests _poll_generation_status
# ===========================================================================


class TestPollGenerationStatus:
    PATCH_GET = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.get"
    PATCH_SLEEP = "wakastart_leads.crews.analysis.tools.gamma_tool.time.sleep"

    def test_completed_immediately(self, gamma_tool, mock_response):
        resp = mock_response(200, {"status": "completed", "gammaUrl": "https://gamma.app/docs/xyz"})
        with patch(self.PATCH_GET, return_value=resp), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("xyz", "test-key")
            assert result == "https://gamma.app/docs/xyz"

    def test_pending_then_completed(self, gamma_tool, mock_response):
        pending = mock_response(200, {"status": "pending"})
        completed = mock_response(200, {"status": "completed", "gammaUrl": "https://gamma.app/docs/final"})
        with patch(self.PATCH_GET, side_effect=[pending, completed]), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("final", "test-key")
            assert result == "https://gamma.app/docs/final"

    def test_failed_status(self, gamma_tool, mock_response):
        resp = mock_response(200, {"status": "failed", "error": "Generation failed"})
        with patch(self.PATCH_GET, return_value=resp), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("fail_id", "test-key")
            assert "echouee" in result.lower()

    def test_error_status(self, gamma_tool, mock_response):
        resp = mock_response(200, {"status": "error", "message": "Something wrong"})
        with patch(self.PATCH_GET, return_value=resp), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("err_id", "test-key")
            assert "echouee" in result.lower()

    def test_url_field_fallback(self, gamma_tool, mock_response):
        # Pas de gammaUrl, mais un champ "url"
        resp = mock_response(200, {"status": "completed", "url": "https://gamma.app/docs/fallback"})
        with patch(self.PATCH_GET, return_value=resp), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("fb_id", "test-key")
            assert result == "https://gamma.app/docs/fallback"

    def test_doc_url_fallback(self, gamma_tool, mock_response):
        resp = mock_response(200, {"status": "completed", "docUrl": "https://gamma.app/docs/doc123"})
        with patch(self.PATCH_GET, return_value=resp), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("doc_id", "test-key")
            assert result == "https://gamma.app/docs/doc123"

    def test_no_url_field(self, gamma_tool, mock_response):
        resp = mock_response(200, {"status": "completed"})
        with patch(self.PATCH_GET, return_value=resp), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("no_url", "test-key")
            assert "introuvable" in result.lower() or "URL" in result

    def test_timeout_max_retries(self, gamma_tool, mock_response):
        pending = mock_response(200, {"status": "pending"})
        with patch(self.PATCH_GET, return_value=pending), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("timeout_id", "test-key", poll_interval=1, max_retries=3)
            assert "Timeout" in result
            assert "3s" in result  # max_retries * poll_interval = 3 * 1 = 3s

    def test_auth_error(self, gamma_tool, mock_response):
        # Tous les polls retournent 401 -> le loop continue mais finit en timeout
        # Sauf si status_code in (401, 403) -> retourne immediatement
        resp = mock_response(401, text="Unauthorized")
        with patch(self.PATCH_GET, return_value=resp), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("auth_id", "bad-key", poll_interval=1, max_retries=3)
            assert "Authentification" in result or "Timeout" in result

    def test_non_200_non_auth_retries(self, gamma_tool, mock_response):
        """Un status 500 pendant le polling est retry puis reussit."""
        error_resp = mock_response(500, text="Server error")
        ok_resp = mock_response(200, {"status": "completed", "gammaUrl": "https://gamma.app/docs/retry"})
        with patch(self.PATCH_GET, side_effect=[error_resp, ok_resp]), patch(self.PATCH_SLEEP):
            result = gamma_tool._poll_generation_status("retry_id", "test-key")
            assert result == "https://gamma.app/docs/retry"

    def test_network_error_during_polling(self, gamma_tool, mock_response):
        """Une erreur reseau pendant le polling est capturee et le polling continue."""
        ok_resp = mock_response(200, {"status": "completed", "gammaUrl": "https://gamma.app/docs/net"})
        with (
            patch(self.PATCH_GET, side_effect=[requests.exceptions.ConnectionError("net err"), ok_resp]),
            patch(self.PATCH_SLEEP),
        ):
            result = gamma_tool._poll_generation_status("net_id", "test-key")
            assert result == "https://gamma.app/docs/net"


# ===========================================================================
# Tests _run - Exceptions supplementaires
# ===========================================================================


class TestGammaRunExceptions:
    PATCH_POST = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.post"
    PATCH_HEAD = "wakastart_leads.crews.analysis.tools.gamma_tool.requests.head"
    SAMPLE_PROMPT = "Test prompt"
    SAMPLE_NAME = "TestCorp"
    SAMPLE_DOMAIN = "testcorp.com"

    def _mock_head_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        return mock_resp

    def test_connection_error(self, gamma_tool, mock_gamma_api_key):
        """requests.exceptions.RequestException est capturee."""
        with (
            patch(self.PATCH_POST, side_effect=requests.exceptions.ConnectionError("refused")),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "connexion" in result.lower()

    def test_generic_exception(self, gamma_tool, mock_gamma_api_key):
        """Une exception generique (non-requests) est capturee proprement."""
        with (
            patch(self.PATCH_POST, side_effect=ValueError("unexpected")),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            assert "inattendue" in result.lower()


# ===========================================================================
# Tests _sanitize_slug
# ===========================================================================


class TestSanitizeSlug:
    """Tests pour la methode _sanitize_slug."""

    @pytest.fixture
    def gamma_tool(self):
        return GammaCreateTool()

    def test_simple_name(self, gamma_tool):
        """Un nom simple est converti en minuscules avec tirets."""
        assert gamma_tool._sanitize_slug("France-Care") == "france-care"

    def test_name_with_accents(self, gamma_tool):
        """Les accents sont normalises."""
        assert gamma_tool._sanitize_slug("Société Générale") == "societe-generale"

    def test_name_with_special_chars(self, gamma_tool):
        """Les caracteres speciaux sont remplaces par des tirets."""
        assert gamma_tool._sanitize_slug("AI & ML Corp.") == "ai-ml-corp"

    def test_empty_name_returns_prospect(self, gamma_tool):
        """Un nom vide retourne 'prospect'."""
        assert gamma_tool._sanitize_slug("") == "prospect"

    def test_only_special_chars_returns_prospect(self, gamma_tool):
        """Un nom avec uniquement des caracteres speciaux retourne 'prospect'."""
        assert gamma_tool._sanitize_slug("@#$%") == "prospect"


# ===========================================================================
# Tests _get_linkener_token
# ===========================================================================


class TestGetLinkenerToken:
    """Tests pour la methode _get_linkener_token."""

    @pytest.fixture
    def gamma_tool(self):
        return GammaCreateTool()

    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_returns_token_on_success(self, mock_post, gamma_tool):
        """Retourne le token si l'authentification reussit."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "abc123token"
        mock_post.return_value = mock_response

        token = gamma_tool._get_linkener_token("https://url.wakastart.com/api", "user", "pass")

        assert token == "abc123token"
        mock_post.assert_called_once_with(
            "https://url.wakastart.com/api/auth/new_token",
            json={"username": "user", "password": "pass"},
            timeout=10,
        )

    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_returns_none_on_auth_failure(self, mock_post, gamma_tool):
        """Retourne None si l'authentification echoue (401)."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        token = gamma_tool._get_linkener_token("https://url.wakastart.com/api", "user", "wrongpass")

        assert token is None

    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_returns_none_on_request_exception(self, mock_post, gamma_tool):
        """Retourne None si une exception reseau se produit."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        token = gamma_tool._get_linkener_token("https://url.wakastart.com/api", "user", "pass")

        assert token is None

    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_returns_none_on_empty_token(self, mock_post, gamma_tool):
        """Retourne None si l'API retourne un body vide ou whitespace."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "   \n  "  # Whitespace only

        mock_post.return_value = mock_response

        token = gamma_tool._get_linkener_token("https://url.wakastart.com/api", "user", "pass")

        assert token is None


# ===========================================================================
# Tests _create_linkener_url
# ===========================================================================


class TestCreateLinkenerUrl:
    """Tests pour la methode _create_linkener_url."""

    @pytest.fixture
    def gamma_tool(self):
        return GammaCreateTool()

    @patch.dict(
        os.environ,
        {
            "LINKENER_API_BASE": "https://url.wakastart.com/api",
            "LINKENER_USERNAME": "testuser",
            "LINKENER_PASSWORD": "testpass",
        },
    )
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_creates_short_url_on_success(self, mock_post, gamma_tool):
        """Cree un lien court et retourne l'URL complete."""
        # Mock auth token response
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.text = "test_token"

        # Mock create URL response
        mock_url_response = MagicMock()
        mock_url_response.status_code = 201

        mock_post.side_effect = [mock_auth_response, mock_url_response]

        result = gamma_tool._create_linkener_url("https://gamma.app/docs/xxx", "France Care")

        assert result == "https://url.wakastart.com/france-care"

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_none_when_env_vars_missing(self, gamma_tool):
        """Retourne None si les variables d'environnement manquent."""
        result = gamma_tool._create_linkener_url("https://gamma.app/docs/xxx", "TestCorp")
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LINKENER_API_BASE": "https://url.wakastart.com/api",
            "LINKENER_USERNAME": "testuser",
            "LINKENER_PASSWORD": "testpass",
        },
    )
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_returns_none_when_auth_fails(self, mock_post, gamma_tool):
        """Retourne None si l'authentification echoue."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result = gamma_tool._create_linkener_url("https://gamma.app/docs/xxx", "TestCorp")

        assert result is None

    @patch.dict(
        os.environ,
        {
            "LINKENER_API_BASE": "https://url.wakastart.com/api",
            "LINKENER_USERNAME": "testuser",
            "LINKENER_PASSWORD": "testpass",
        },
    )
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.time.time", return_value=1234567890.123)
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_adds_suffix_on_slug_conflict(self, mock_post, mock_time, gamma_tool):
        """Ajoute un suffixe numerique si le slug existe deja (409)."""
        # Mock auth
        mock_auth = MagicMock()
        mock_auth.status_code = 200
        mock_auth.text = "token"

        # Mock first create (conflict)
        mock_conflict = MagicMock()
        mock_conflict.status_code = 409

        # Mock retry create (success)
        mock_success = MagicMock()
        mock_success.status_code = 201

        mock_post.side_effect = [mock_auth, mock_conflict, mock_success]

        result = gamma_tool._create_linkener_url("https://gamma.app/docs/xxx", "TestCorp")

        # Le suffixe est 1234567890 % 1000 = 890
        assert result == "https://url.wakastart.com/testcorp-890"

    @patch.dict(
        os.environ,
        {
            "LINKENER_API_BASE": "https://url.wakastart.com/api",
            "LINKENER_USERNAME": "testuser",
            "LINKENER_PASSWORD": "testpass",
        },
    )
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.time.time", return_value=1234567890.123)
    @patch("wakastart_leads.crews.analysis.tools.gamma_tool.requests.post")
    def test_returns_none_on_retry_exception(self, mock_post, mock_time, gamma_tool):
        """Retourne None si une exception reseau se produit pendant le retry 409."""
        # Mock auth
        mock_auth = MagicMock()
        mock_auth.status_code = 200
        mock_auth.text = "token"

        # Mock first create (conflict 409)
        mock_conflict = MagicMock()
        mock_conflict.status_code = 409

        # Mock retry raises exception
        mock_post.side_effect = [
            mock_auth,
            mock_conflict,
            requests.exceptions.RequestException("Network error during retry"),
        ]

        result = gamma_tool._create_linkener_url("https://gamma.app/docs/xxx", "TestCorp")

        assert result is None
