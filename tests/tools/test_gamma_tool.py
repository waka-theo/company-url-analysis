"""Tests unitaires pour GammaCreateTool."""

from unittest.mock import patch

import pytest
import requests

from company_url_analysis_automation.tools.gamma_tool import (
    GAMMA_TEMPLATE_ID,
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
# Tests _run
# ===========================================================================


class TestGammaRun:
    PATCH_POST = "company_url_analysis_automation.tools.gamma_tool.requests.post"
    PATCH_GET = "company_url_analysis_automation.tools.gamma_tool.requests.get"
    PATCH_SLEEP = "company_url_analysis_automation.tools.gamma_tool.time.sleep"
    SAMPLE_PROMPT = "WakaStellar - SaaS B2B - Migration legacy"

    def test_missing_api_key(self, gamma_tool, clear_all_api_keys):
        result = gamma_tool._run(self.SAMPLE_PROMPT)
        assert "GAMMA_API_KEY non configuree" in result

    def test_success_calls_poll(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(200, {"generationId": "gen123"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response),
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_SLEEP),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "https://gamma.app/docs/abc123" in result

    def test_http_400(self, gamma_tool, mock_gamma_api_key, mock_response):
        resp = mock_response(400, {"message": "Invalid prompt"}, text="Bad Request")
        with patch(self.PATCH_POST, return_value=resp):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "validation" in result.lower() or "Invalid prompt" in result

    def test_http_403(self, gamma_tool, mock_gamma_api_key, mock_response):
        with patch(self.PATCH_POST, return_value=mock_response(403, text="Forbidden")):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "invalide" in result.lower() or "permissions" in result.lower()

    def test_http_429(self, gamma_tool, mock_gamma_api_key, mock_response):
        with patch(self.PATCH_POST, return_value=mock_response(429)):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "Limite" in result or "requetes" in result

    def test_http_500(self, gamma_tool, mock_gamma_api_key, mock_response):
        with patch(self.PATCH_POST, return_value=mock_response(500, text="Server error")):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "code 500" in result

    def test_no_generation_id(self, gamma_tool, mock_gamma_api_key, mock_response):
        with patch(self.PATCH_POST, return_value=mock_response(200, {})):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "sans generationId" in result

    def test_timeout(self, gamma_tool, mock_gamma_api_key):
        with patch(self.PATCH_POST, side_effect=requests.exceptions.Timeout):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "Timeout" in result
            assert "120s" in result

    def test_status_201(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(201, {"generationId": "gen201"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response),
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_SLEEP),
        ):
            result = gamma_tool._run(self.SAMPLE_PROMPT)
            assert "gamma.app" in result

    def test_correct_payload(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(200, {"generationId": "gen_payload"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response) as mock_post,
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_SLEEP),
        ):
            gamma_tool._run(self.SAMPLE_PROMPT)
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["gammaId"] == GAMMA_TEMPLATE_ID
            assert payload["prompt"] == self.SAMPLE_PROMPT
            assert payload["sharingOptions"]["workspaceAccess"] == "view"
            assert payload["sharingOptions"]["externalAccess"] == "view"

    def test_uses_template_id(self, gamma_tool, mock_gamma_api_key, mock_response, gamma_completed_status):
        post_response = mock_response(200, {"generationId": "gen_tpl"})
        get_response = mock_response(200, gamma_completed_status)
        with (
            patch(self.PATCH_POST, return_value=post_response) as mock_post,
            patch(self.PATCH_GET, return_value=get_response),
            patch(self.PATCH_SLEEP),
        ):
            gamma_tool._run(self.SAMPLE_PROMPT)
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["gammaId"] == "g_w56csm22x0u632h"


# ===========================================================================
# Tests _poll_generation_status
# ===========================================================================


class TestPollGenerationStatus:
    PATCH_GET = "company_url_analysis_automation.tools.gamma_tool.requests.get"
    PATCH_SLEEP = "company_url_analysis_automation.tools.gamma_tool.time.sleep"

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
