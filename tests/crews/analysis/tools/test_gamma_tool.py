"""Tests unitaires pour GammaCreateTool."""

from unittest.mock import MagicMock, patch

import pytest
import requests

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
        with pytest.raises(Exception):
            GammaCreateInput(prompt="Test", company_domain="test.com")

    def test_missing_company_domain_raises(self):
        with pytest.raises(Exception):
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
            assert result == f"{UNAVATAR_BASE}/wakastellar.com"

    def test_unavatar_404_falls_back_to_google(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._resolve_company_logo("unknown.xyz", "Unknown")
            assert "google.com/s2/favicons" in result
            assert "unknown.xyz" in result

    def test_unavatar_timeout_falls_back_to_google(self, gamma_tool):
        with patch(self.PATCH_HEAD, side_effect=requests.exceptions.Timeout):
            result = gamma_tool._resolve_company_logo("slow.com", "Slow")
            assert "google.com/s2/favicons" in result

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
            result = gamma_tool._build_enhanced_prompt(
                "Base prompt", "testcorp.com", "TestCorp"
            )
            assert "Base prompt" in result
            assert f"{UNAVATAR_BASE}/testcorp.com" in result
            assert OPPORTUNITY_ANALYSIS_IMAGE_URL in result
            assert WAKASTELLAR_LOGO_URL in result

    def test_includes_placement_instructions(self, gamma_tool):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._build_enhanced_prompt(
                "Base prompt", "testcorp.com", "TestCorp"
            )
            assert "IMAGES POUR LA PREMIERE PAGE" in result
            assert "A gauche" in result
            assert "Au centre" in result
            assert "A droite" in result

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
            result = gamma_tool._build_enhanced_prompt(
                original, "test.com", "Test"
            )
            assert result.startswith(original)

    def test_includes_sizing_instructions(self, gamma_tool):
        """Le prompt doit contenir des instructions explicites de dimensionnement."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch(self.PATCH_HEAD, return_value=mock_resp):
            result = gamma_tool._build_enhanced_prompt(
                "Base prompt", "testcorp.com", "TestCorp"
            )
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

    def test_correct_payload_uses_enhanced_prompt(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(200, {"generationId": "gen_payload"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response) as mock_post,
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_HEAD, return_value=self._mock_head_success()),
            patch(self.PATCH_SLEEP),
        ):
            gamma_tool._run(self.SAMPLE_PROMPT, self.SAMPLE_NAME, self.SAMPLE_DOMAIN)
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["gammaId"] == GAMMA_TEMPLATE_ID
            # Le prompt doit etre enrichi (contient le prompt original + les images)
            assert self.SAMPLE_PROMPT in payload["prompt"]
            assert "IMAGES POUR LA PREMIERE PAGE" in payload["prompt"]
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
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["gammaId"] == "g_w56csm22x0u632h"


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

    def test_docUrl_fallback(self, gamma_tool, mock_response):
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
