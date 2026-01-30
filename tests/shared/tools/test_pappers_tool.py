"""Tests unitaires pour PappersSearchTool."""

from unittest.mock import patch

import pytest
import requests

from wakastart_leads.shared.tools.pappers_tool import PappersSearchInput, PappersSearchTool


# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestPappersToolInstantiation:
    def test_tool_name(self, pappers_tool):
        assert pappers_tool.name == "pappers_search"

    def test_tool_args_schema(self, pappers_tool):
        assert pappers_tool.args_schema is PappersSearchInput


# ===========================================================================
# Tests _run - Detection SIREN vs nom
# ===========================================================================


class TestPappersRunDetection:
    PATCH_TARGET = "wakastart_leads.shared.tools.pappers_tool.requests.get"

    def test_missing_api_key(self, pappers_tool, clear_all_api_keys):
        result = pappers_tool._run("WakaStellar")
        assert "PAPPERS_API_KEY non configuree" in result

    def test_detects_siren_9_digits(self, pappers_tool, mock_pappers_api_key, mock_response, pappers_company_detail):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, pappers_company_detail)) as mock_get:
            pappers_tool._run("123456789")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/entreprise" in called_url
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            assert params["siren"] == "123456789"

    def test_detects_siren_with_spaces(self, pappers_tool, mock_pappers_api_key, mock_response, pappers_company_detail):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, pappers_company_detail)) as mock_get:
            pappers_tool._run("123 456 789")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/entreprise" in called_url

    def test_name_not_siren(self, pappers_tool, mock_pappers_api_key, mock_response, pappers_search_results):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, pappers_search_results)) as mock_get:
            pappers_tool._run("WakaStellar")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/recherche" in called_url
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            assert params["q"] == "WakaStellar"

    def test_8_digits_not_siren(self, pappers_tool, mock_pappers_api_key, mock_response, pappers_search_results):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, pappers_search_results)) as mock_get:
            pappers_tool._run("12345678")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/recherche" in called_url

    def test_10_digits_not_siren(self, pappers_tool, mock_pappers_api_key, mock_response, pappers_search_results):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, pappers_search_results)) as mock_get:
            pappers_tool._run("1234567890")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/recherche" in called_url

    def test_alphanumeric_not_siren(self, pappers_tool, mock_pappers_api_key, mock_response, pappers_search_results):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, pappers_search_results)) as mock_get:
            pappers_tool._run("SAS123456")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/recherche" in called_url


# ===========================================================================
# Tests _run - Erreurs HTTP
# ===========================================================================


class TestPappersRunErrors:
    PATCH_TARGET = "wakastart_leads.shared.tools.pappers_tool.requests.get"

    def test_http_401(self, pappers_tool, mock_pappers_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(401, text="Unauthorized")):
            result = pappers_tool._run("WakaStellar")
            assert "invalide ou expiree" in result

    def test_http_404(self, pappers_tool, mock_pappers_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(404)):
            result = pappers_tool._run("WakaStellar")
            assert "Aucune entreprise trouvee" in result

    def test_http_500(self, pappers_tool, mock_pappers_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(500, text="Server error")):
            result = pappers_tool._run("WakaStellar")
            assert "code 500" in result

    def test_timeout(self, pappers_tool, mock_pappers_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.Timeout):
            result = pappers_tool._run("WakaStellar")
            assert "Timeout" in result

    def test_network_error(self, pappers_tool, mock_pappers_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError("Connection refused")):
            result = pappers_tool._run("WakaStellar")
            assert "connexion" in result.lower()


# ===========================================================================
# Tests _format_company_details (methode pure)
# ===========================================================================


class TestFormatCompanyDetails:
    def test_full_details(self, pappers_tool, pappers_company_detail):
        result = pappers_tool._format_company_details(pappers_company_detail)
        assert "123456789" in result
        assert "12345678900015" in result
        assert "SAS" in result
        assert "2020-01-15" in result
        assert "Jean Dupont" in result
        assert "President" in result

    def test_missing_finances(self, pappers_tool):
        data = {
            "siren": "111111111",
            "nom_entreprise": "TestCorp",
            "forme_juridique": "SAS",
            "siege": {},
        }
        result = pappers_tool._format_company_details(data)
        assert "TestCorp" in result
        # Pas de crash, les champs financiers sont absents

    def test_entreprise_cessee(self, pappers_tool):
        data = {
            "nom_entreprise": "ClosedCorp",
            "entreprise_cessee": True,
            "siege": {},
        }
        result = pappers_tool._format_company_details(data)
        assert "Cessee" in result

    def test_entreprise_active(self, pappers_tool):
        data = {
            "nom_entreprise": "ActiveCorp",
            "entreprise_cessee": False,
            "siege": {},
        }
        result = pappers_tool._format_company_details(data)
        assert "Active" in result

    def test_dirigeants_max_5(self, pappers_tool):
        representants = [{"nom_complet": f"Dirigeant {i}", "qualite": "Admin"} for i in range(10)]
        data = {"nom_entreprise": "BigCorp", "siege": {}, "representants": representants}
        result = pappers_tool._format_company_details(data)
        # Seuls 5 dirigeants doivent apparaitre
        assert "Dirigeant 0" in result
        assert "Dirigeant 4" in result
        assert "Dirigeant 5" not in result

    def test_beneficiaires_max_3(self, pappers_tool):
        beneficiaires = [{"prenom": f"Ben{i}", "nom": "Test", "pourcentage_parts": 10} for i in range(6)]
        data = {"nom_entreprise": "BigCorp", "siege": {}, "beneficiaires_effectifs": beneficiaires}
        result = pappers_tool._format_company_details(data)
        assert "Ben0" in result
        assert "Ben2" in result
        assert "Ben3" not in result

    def test_nom_fallback_denomination(self, pappers_tool):
        data = {
            "nom_entreprise": None,
            "denomination": "FallbackCorp",
            "siege": {},
        }
        result = pappers_tool._format_company_details(data)
        assert "FallbackCorp" in result

    def test_nom_complet_concat(self, pappers_tool):
        data = {
            "nom_entreprise": "TestCorp",
            "siege": {},
            "representants": [{"prenom": "Pierre", "nom": "Durand", "qualite": "Admin"}],
        }
        result = pappers_tool._format_company_details(data)
        assert "Pierre Durand" in result


# ===========================================================================
# Tests _format_search_results (methode pure)
# ===========================================================================


class TestFormatSearchResults:
    def test_with_results(self, pappers_tool, pappers_search_results):
        result = pappers_tool._format_search_results(pappers_search_results, "WakaStellar")
        assert "WakaStellar SAS" in result
        assert "123456789" in result
        assert "Paris" in result
        assert "WakaTest SARL" in result

    def test_no_results(self, pappers_tool):
        result = pappers_tool._format_search_results({}, "InexistantCorp")
        assert "Aucune entreprise trouvee" in result

    def test_max_5_results(self, pappers_tool):
        results = [
            {"nom_entreprise": f"Corp{i}", "siren": f"10000000{i}", "siege": {"ville": "Paris"}}
            for i in range(10)
        ]
        data = {"resultats_nom_entreprise": results}
        result = pappers_tool._format_search_results(data, "Corp")
        assert "Corp0" in result
        assert "Corp4" in result
        assert "Corp5" not in result


# ===========================================================================
# Tests _run - Exception generique
# ===========================================================================


class TestPappersRunGenericException:
    PATCH_TARGET = "wakastart_leads.shared.tools.pappers_tool.requests.get"

    def test_generic_exception(self, pappers_tool, mock_pappers_api_key):
        """Une exception generique (non-requests) est capturee proprement."""
        with patch(self.PATCH_TARGET, side_effect=ValueError("unexpected")):
            result = pappers_tool._run("WakaStellar")
            assert "inattendue" in result.lower()
