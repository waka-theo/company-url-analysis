"""Tests unitaires pour KasprEnrichTool."""

from unittest.mock import patch

import pytest
import requests

from company_url_analysis_automation.tools.kaspr_tool import KasprEnrichInput, KasprEnrichTool


# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestKasprToolInstantiation:
    def test_tool_name(self, kaspr_tool):
        assert kaspr_tool.name == "kaspr_enrich"

    def test_tool_args_schema(self, kaspr_tool):
        assert kaspr_tool.args_schema is KasprEnrichInput


# ===========================================================================
# Tests _extract_linkedin_id (methode pure, pas de mock)
# ===========================================================================


class TestExtractLinkedinId:
    def test_standard_url(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://www.linkedin.com/in/john-doe")
        assert result == "john-doe"

    def test_trailing_slash(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://www.linkedin.com/in/john-doe/")
        assert result == "john-doe"

    def test_query_params(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://www.linkedin.com/in/john-doe?locale=fr")
        assert result == "john-doe"

    def test_pub_format(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://www.linkedin.com/pub/jane-smith")
        assert result == "jane-smith"

    def test_fr_subdomain(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://fr.linkedin.com/in/pierre-dupont")
        assert result == "pierre-dupont"

    def test_case_insensitive(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://WWW.LINKEDIN.COM/IN/John-Doe")
        assert result == "John-Doe"

    def test_invalid_url(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://twitter.com/johndoe")
        assert result is None

    def test_sales_navigator(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://www.linkedin.com/sales/lead/ACwAAA")
        assert result is None

    def test_empty_string(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("")
        assert result is None

    def test_root_linkedin(self, kaspr_tool):
        result = kaspr_tool._extract_linkedin_id("https://www.linkedin.com")
        assert result is None


# ===========================================================================
# Tests _format_contact_info (methode pure, pas de mock)
# ===========================================================================


class TestFormatContactInfo:
    def test_full_data(self, kaspr_tool, kaspr_full_response):
        result = kaspr_tool._format_contact_info(
            kaspr_full_response, "Jean Dupont", "https://www.linkedin.com/in/jean-dupont"
        )
        assert "jean.dupont@company.com" in result
        assert "+33612345678" in result
        assert "CTO" in result
        assert "WakaStellar" in result

    def test_starry_fallback(self, kaspr_tool, kaspr_starry_response):
        result = kaspr_tool._format_contact_info(
            kaspr_starry_response, "Jean Dupont", "https://www.linkedin.com/in/jean-dupont"
        )
        assert "j***@company.com" in result
        assert "+336****5678" in result

    def test_no_contact(self, kaspr_tool, kaspr_empty_response):
        result = kaspr_tool._format_contact_info(
            kaspr_empty_response, "Jean Dupont", "https://www.linkedin.com/in/jean-dupont"
        )
        assert "Non trouvé" in result

    def test_only_personal_email(self, kaspr_tool):
        data = {
            "profile": {
                "professionalEmails": [],
                "personalEmails": ["perso@gmail.com"],
                "phones": [],
            }
        }
        result = kaspr_tool._format_contact_info(data, "Test User", "https://linkedin.com/in/test")
        assert "perso@gmail.com" in result

    def test_pro_priority_over_starry(self, kaspr_tool):
        data = {
            "profile": {
                "professionalEmails": ["pro@company.com"],
                "starryProfessionalEmail": "p***@company.com",
                "personalEmails": [],
                "phones": [],
            }
        }
        result = kaspr_tool._format_contact_info(data, "Test User", "https://linkedin.com/in/test")
        assert "pro@company.com" in result
        assert "p***@company.com" not in result

    def test_nested_profile(self, kaspr_tool, kaspr_full_response):
        # kaspr_full_response est deja neste sous "profile"
        result = kaspr_tool._format_contact_info(
            kaspr_full_response, "Jean Dupont", "https://linkedin.com/in/jean"
        )
        assert "jean.dupont@company.com" in result

    def test_flat_response(self, kaspr_tool):
        # Donnees directement au niveau racine, pas de cle "profile"
        data = {
            "professionalEmails": ["flat@test.com"],
            "personalEmails": [],
            "phones": ["+33100000000"],
            "title": "Dev",
            "company": {"name": "FlatCorp"},
        }
        result = kaspr_tool._format_contact_info(data, "Flat User", "https://linkedin.com/in/flat")
        assert "flat@test.com" in result
        assert "+33100000000" in result
        assert "Dev" in result
        assert "FlatCorp" in result

    def test_company_not_dict(self, kaspr_tool):
        data = {
            "profile": {
                "professionalEmails": [],
                "personalEmails": [],
                "phones": [],
                "title": "CEO",
                "company": "JusteUneString",
            }
        }
        # Ne doit pas crasher
        result = kaspr_tool._format_contact_info(data, "Test", "https://linkedin.com/in/test")
        assert "CEO" in result
        # company_name ne sera pas affiche car isinstance(company, dict) est False
        assert "JusteUneString" not in result

    def test_header_contains_name(self, kaspr_tool, kaspr_full_response):
        result = kaspr_tool._format_contact_info(
            kaspr_full_response, "Jean Dupont", "https://linkedin.com/in/jean"
        )
        assert result.startswith("**Contact: Jean Dupont**")


# ===========================================================================
# Tests _run (mock requests.post + env vars)
# ===========================================================================


class TestKasprRun:
    PATCH_TARGET = "company_url_analysis_automation.tools.kaspr_tool.requests.post"
    VALID_LINKEDIN = "https://www.linkedin.com/in/jean-dupont"
    VALID_NAME = "Jean Dupont"

    def test_missing_api_key(self, kaspr_tool, clear_all_api_keys):
        result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
        assert "KASPR_API_KEY non configurée" in result

    def test_invalid_linkedin_url(self, kaspr_tool, mock_kaspr_api_key):
        with patch(self.PATCH_TARGET) as mock_post:
            result = kaspr_tool._run("https://twitter.com/johndoe", self.VALID_NAME)
            assert "URL LinkedIn invalide" in result
            mock_post.assert_not_called()

    def test_success_200(self, kaspr_tool, mock_kaspr_api_key, mock_response, kaspr_full_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, kaspr_full_response)):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "jean.dupont@company.com" in result
            assert "Jean Dupont" in result

    def test_http_401(self, kaspr_tool, mock_kaspr_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(401, text="Unauthorized")):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "invalide ou expirée" in result

    def test_http_402(self, kaspr_tool, mock_kaspr_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(402, text="Payment required")):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "insuffisants" in result

    def test_http_404(self, kaspr_tool, mock_kaspr_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(404)):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "Aucun contact trouvé" in result
            assert self.VALID_NAME in result

    def test_http_429(self, kaspr_tool, mock_kaspr_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(429)):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "Limite de requêtes" in result

    def test_http_500(self, kaspr_tool, mock_kaspr_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(500, text="Server error")):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "code 500" in result

    def test_timeout(self, kaspr_tool, mock_kaspr_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.Timeout):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "Timeout" in result

    def test_network_error(self, kaspr_tool, mock_kaspr_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError("Connection refused")):
            result = kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            assert "connexion" in result.lower()

    def test_correct_headers(self, kaspr_tool, mock_kaspr_api_key, mock_response, kaspr_full_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, kaspr_full_response)) as mock_post:
            kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            call_kwargs = mock_post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
            assert "Bearer test-kaspr-key-12345" in headers["Authorization"]
            assert headers["accept-version"] == "v2.0"
            assert headers["Accept"] == "application/json"
            assert headers["Content-Type"] == "application/json"

    def test_correct_payload(self, kaspr_tool, mock_kaspr_api_key, mock_response, kaspr_full_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, kaspr_full_response)) as mock_post:
            kaspr_tool._run(self.VALID_LINKEDIN, self.VALID_NAME)
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
            assert payload["id"] == "jean-dupont"
            assert payload["name"] == self.VALID_NAME
            assert payload["dataToGet"] == ["phone", "workEmail", "directEmail"]
