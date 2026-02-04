"""Tests unitaires pour ZeliqEmailEnrichTool."""

from unittest.mock import patch

import pytest
import requests

from wakastart_leads.crews.analysis.tools.zeliq_tool import (
    ZeliqEmailEnrichInput,
    ZeliqEmailEnrichTool,
)


# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestZeliqToolInstantiation:
    def test_tool_name(self, zeliq_tool):
        assert zeliq_tool.name == "zeliq_email_enrich"

    def test_tool_args_schema(self, zeliq_tool):
        assert zeliq_tool.args_schema is ZeliqEmailEnrichInput


# ===========================================================================
# Tests _create_webhook_url
# ===========================================================================


class TestCreateWebhookUrl:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.post"

    def test_returns_url_and_uuid(self, zeliq_tool, mock_response, webhook_site_token_response):
        """Retourne l'URL du webhook et l'UUID du token."""
        with patch(self.PATCH_TARGET, return_value=mock_response(201, webhook_site_token_response)):
            webhook_url, token_uuid = zeliq_tool._create_webhook_url()
            assert webhook_url == "https://webhook.site/abc123-def456-ghi789"
            assert token_uuid == "abc123-def456-ghi789"

    def test_calls_webhook_site_api(self, zeliq_tool, mock_response, webhook_site_token_response):
        """Appelle l'API webhook.site pour creer un token."""
        with patch(self.PATCH_TARGET, return_value=mock_response(201, webhook_site_token_response)) as mock_post:
            zeliq_tool._create_webhook_url()
            mock_post.assert_called_once()
            call_url = mock_post.call_args[0][0]
            assert "webhook.site/token" in call_url

    def test_handles_webhook_site_error(self, zeliq_tool, mock_response):
        """Gere les erreurs de webhook.site."""
        with patch(self.PATCH_TARGET, return_value=mock_response(500)):
            with pytest.raises(RuntimeError, match="webhook.site"):
                zeliq_tool._create_webhook_url()

    def test_handles_network_error(self, zeliq_tool):
        """Gere les erreurs reseau."""
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError):
            with pytest.raises(RuntimeError, match="connexion"):
                zeliq_tool._create_webhook_url()


# ===========================================================================
# Tests _call_zeliq_api
# ===========================================================================


class TestCallZeliqApi:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.post"

    def test_returns_true_on_success(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Retourne True si l'appel API reussit."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, {"status": "processing"})):
            result = zeliq_tool._call_zeliq_api(
                first_name="Patrick",
                last_name="Collison",
                company="stripe.com",
                linkedin_url="https://linkedin.com/in/patrickcollison",
                callback_url="https://webhook.site/abc123",
            )
            assert result is True

    def test_sends_correct_payload(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Envoie le bon payload a l'API Zeliq."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, {})) as mock_post:
            zeliq_tool._call_zeliq_api(
                first_name="Jean",
                last_name="Dupont",
                company="acme.com",
                linkedin_url="https://linkedin.com/in/jeandupont",
                callback_url="https://webhook.site/xyz789",
            )
            call_kwargs = mock_post.call_args.kwargs
            payload = call_kwargs.get("json")
            assert payload["first_name"] == "Jean"
            assert payload["last_name"] == "Dupont"
            assert payload["company"] == "acme.com"
            assert payload["linkedin_url"] == "https://linkedin.com/in/jeandupont"
            assert payload["callback_url"] == "https://webhook.site/xyz789"

    def test_sends_correct_headers(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Envoie le header x-api-key."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, {})) as mock_post:
            zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )
            call_kwargs = mock_post.call_args.kwargs
            headers = call_kwargs.get("headers")
            assert headers["x-api-key"] == "test-zeliq-key-12345"

    def test_missing_api_key_raises_error(self, zeliq_tool, clear_all_api_keys):
        """Leve une erreur si la cle API est absente."""
        with pytest.raises(ValueError, match="ZELIQ_API_KEY"):
            zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )

    def test_handles_401_error(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Gere l'erreur 401 (cle invalide)."""
        with patch(self.PATCH_TARGET, return_value=mock_response(401)):
            result = zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )
            assert result is False

    def test_handles_400_error(self, zeliq_tool, mock_zeliq_api_key, mock_response):
        """Gere l'erreur 400 (validation)."""
        with patch(self.PATCH_TARGET, return_value=mock_response(400)):
            result = zeliq_tool._call_zeliq_api(
                first_name="Test",
                last_name="User",
                company="test.com",
                linkedin_url="https://linkedin.com/in/test",
                callback_url="https://webhook.site/test",
            )
            assert result is False


# ===========================================================================
# Tests _poll_webhook
# ===========================================================================


class TestPollWebhook:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.zeliq_tool.requests.get"
    PATCH_SLEEP = "wakastart_leads.crews.analysis.tools.zeliq_tool.time.sleep"

    def test_returns_data_when_received(
        self, zeliq_tool, mock_response, webhook_site_requests_response
    ):
        """Retourne les donnees quand le webhook recoit une reponse."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, webhook_site_requests_response)):
            with patch(self.PATCH_SLEEP):
                result = zeliq_tool._poll_webhook("abc123-def456-ghi789")
                assert result is not None
                assert result["contact"]["most_probable_email"] == "patrick@stripe.com"

    def test_polls_until_data_received(
        self, zeliq_tool, mock_response, webhook_site_empty_response, webhook_site_requests_response
    ):
        """Poll plusieurs fois jusqu'a reception des donnees."""
        responses = [
            mock_response(200, webhook_site_empty_response),
            mock_response(200, webhook_site_empty_response),
            mock_response(200, webhook_site_requests_response),
        ]
        with patch(self.PATCH_TARGET, side_effect=responses):
            with patch(self.PATCH_SLEEP) as mock_sleep:
                result = zeliq_tool._poll_webhook("abc123")
                assert result is not None
                assert mock_sleep.call_count == 2  # 2 attentes avant succes

    def test_returns_none_on_timeout(self, zeliq_tool, mock_response, webhook_site_empty_response):
        """Retourne None apres timeout."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, webhook_site_empty_response)):
            with patch(self.PATCH_SLEEP):
                # Simuler un timeout en forcant le nombre max d'iterations (ClassVar)
                original_timeout = ZeliqEmailEnrichTool.POLL_TIMEOUT
                original_interval = ZeliqEmailEnrichTool.POLL_INTERVAL
                try:
                    ZeliqEmailEnrichTool.POLL_TIMEOUT = 3
                    ZeliqEmailEnrichTool.POLL_INTERVAL = 1
                    result = zeliq_tool._poll_webhook("abc123")
                    assert result is None
                finally:
                    ZeliqEmailEnrichTool.POLL_TIMEOUT = original_timeout
                    ZeliqEmailEnrichTool.POLL_INTERVAL = original_interval

    def test_calls_correct_endpoint(self, zeliq_tool, mock_response, webhook_site_requests_response):
        """Appelle le bon endpoint webhook.site."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, webhook_site_requests_response)) as mock_get:
            with patch(self.PATCH_SLEEP):
                zeliq_tool._poll_webhook("my-token-uuid")
                call_url = mock_get.call_args[0][0]
                assert "webhook.site/token/my-token-uuid/requests" in call_url

    def test_handles_network_error(self, zeliq_tool):
        """Retourne None sur erreur reseau."""
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError):
            with patch(self.PATCH_SLEEP):
                result = zeliq_tool._poll_webhook("abc123")
                assert result is None