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
