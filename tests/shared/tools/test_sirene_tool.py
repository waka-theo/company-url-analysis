"""Tests unitaires pour SireneSearchTool."""

from unittest.mock import patch

import requests

from wakastart_leads.shared.tools.sirene_tool import SireneSearchInput

# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestSireneToolInstantiation:
    def test_tool_name(self, sirene_tool):
        assert sirene_tool.name == "sirene_search"

    def test_tool_args_schema(self, sirene_tool):
        assert sirene_tool.args_schema is SireneSearchInput

    def test_tool_description_contains_insee(self, sirene_tool):
        assert "INSEE" in sirene_tool.description


# ===========================================================================
# Tests _run - Detection SIREN vs nom
# ===========================================================================


class TestSireneRunDetection:
    PATCH_TARGET = "wakastart_leads.shared.tools.sirene_tool.requests.get"

    def test_missing_api_key(self, sirene_tool, clear_all_api_keys):
        result = sirene_tool._run("Google")
        assert "INSEE_SIRENE_API_KEY non configuree" in result

    def test_detects_siren_9_digits(
        self, sirene_tool, mock_sirene_api_key, mock_response, sirene_unite_legale_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, sirene_unite_legale_response)) as mock_get:
            sirene_tool._run("309634954")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/siren/309634954" in called_url

    def test_detects_siren_with_spaces(
        self, sirene_tool, mock_sirene_api_key, mock_response, sirene_unite_legale_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, sirene_unite_legale_response)) as mock_get:
            sirene_tool._run("309 634 954")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            assert "/siren/309634954" in called_url

    def test_name_not_siren(
        self, sirene_tool, mock_sirene_api_key, mock_response, sirene_search_results_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, sirene_search_results_response)) as mock_get:
            sirene_tool._run("Google")
            call_args = mock_get.call_args
            called_url = call_args.args[0] if call_args.args else call_args[0][0]
            # Recherche multicritere sur /siren avec parametre q
            assert "/siren" in called_url
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            assert "q" in params
            assert "Google" in params["q"]

    def test_8_digits_not_siren(
        self, sirene_tool, mock_sirene_api_key, mock_response, sirene_search_results_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, sirene_search_results_response)) as mock_get:
            sirene_tool._run("12345678")
            call_args = mock_get.call_args
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            # 8 chiffres = pas un SIREN, donc recherche par nom
            assert "q" in params

    def test_10_digits_not_siren(
        self, sirene_tool, mock_sirene_api_key, mock_response, sirene_search_results_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, sirene_search_results_response)) as mock_get:
            sirene_tool._run("1234567890")
            call_args = mock_get.call_args
            params = call_args.kwargs.get("params") or call_args[1].get("params")
            # 10 chiffres = pas un SIREN, donc recherche par nom
            assert "q" in params


# ===========================================================================
# Tests _run - Headers API
# ===========================================================================


class TestSireneApiHeaders:
    PATCH_TARGET = "wakastart_leads.shared.tools.sirene_tool.requests.get"

    def test_api_key_in_header(
        self, sirene_tool, mock_sirene_api_key, mock_response, sirene_unite_legale_response
    ):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, sirene_unite_legale_response)) as mock_get:
            sirene_tool._run("309634954")
            call_args = mock_get.call_args
            headers = call_args.kwargs.get("headers") or call_args[1].get("headers")
            assert "X-INSEE-Api-Key-Integration" in headers
            assert headers["X-INSEE-Api-Key-Integration"] == "test-sirene-key-12345"


# ===========================================================================
# Tests _run - Erreurs HTTP
# ===========================================================================


class TestSireneRunErrors:
    PATCH_TARGET = "wakastart_leads.shared.tools.sirene_tool.requests.get"

    def test_http_401(self, sirene_tool, mock_sirene_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(401, text="Unauthorized")):
            result = sirene_tool._run("Google")
            assert "invalide ou expiree" in result

    def test_http_403(self, sirene_tool, mock_sirene_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(403, text="Forbidden")):
            result = sirene_tool._run("Google")
            assert "souscription" in result.lower()

    def test_http_404(self, sirene_tool, mock_sirene_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(404)):
            result = sirene_tool._run("309634954")
            assert "Aucune entreprise trouvee" in result

    def test_http_500(self, sirene_tool, mock_sirene_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(500, text="Server error")):
            result = sirene_tool._run("Google")
            assert "code 500" in result

    def test_timeout(self, sirene_tool, mock_sirene_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.Timeout):
            result = sirene_tool._run("Google")
            assert "Timeout" in result

    def test_network_error(self, sirene_tool, mock_sirene_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError("Connection refused")):
            result = sirene_tool._run("Google")
            assert "connexion" in result.lower()


# ===========================================================================
# Tests _format_unite_legale (methode pure)
# ===========================================================================


class TestFormatUniteLegale:
    def test_full_details(self, sirene_tool, sirene_unite_legale_response):
        result = sirene_tool._format_unite_legale(sirene_unite_legale_response["uniteLegale"])
        assert "309634954" in result
        assert "GOOGLE FRANCE" in result
        assert "1979-01-01" in result
        assert "Active" in result
        assert "500-999" in result  # tranche effectif 41

    def test_individual_entrepreneur(self, sirene_tool, sirene_individual_response):
        result = sirene_tool._format_unite_legale(sirene_individual_response["uniteLegale"])
        assert "Jean DUPONT" in result
        assert "123456789" in result
        assert "Entrepreneur individuel" in result

    def test_ceased_company(self, sirene_tool, sirene_ceased_response):
        result = sirene_tool._format_unite_legale(sirene_ceased_response["uniteLegale"])
        assert "CLOSED CORP" in result
        assert "Cessée" in result

    def test_missing_periode(self, sirene_tool):
        data = {
            "siren": "111111111",
            "dateCreationUniteLegale": "2020-01-01",
            "periodesUniteLegale": [],
        }
        result = sirene_tool._format_unite_legale(data)
        assert "111111111" in result
        # Pas de crash meme sans periode


# ===========================================================================
# Tests _format_search_results (methode pure)
# ===========================================================================


class TestFormatSearchResults:
    def test_with_results(self, sirene_tool, sirene_search_results_response):
        result = sirene_tool._format_search_results(
            sirene_search_results_response["unitesLegales"], "Google"
        )
        assert "GOOGLE FRANCE" in result
        assert "309634954" in result
        assert "GOOGLE CLOUD FRANCE" in result
        assert "443061841" in result

    def test_no_results(self, sirene_tool):
        result = sirene_tool._format_search_results([], "InexistantCorp")
        assert "Aucune entreprise trouvee" in result

    def test_max_5_results(self, sirene_tool):
        unites = [
            {
                "siren": f"10000000{i}",
                "dateCreationUniteLegale": "2020-01-01",
                "periodesUniteLegale": [
                    {"denominationUniteLegale": f"Corp{i}", "etatAdministratifUniteLegale": "A"}
                ],
            }
            for i in range(10)
        ]
        result = sirene_tool._format_search_results(unites, "Corp")
        assert "Corp0" in result
        assert "Corp4" in result
        assert "Corp5" not in result


# ===========================================================================
# Tests _get_forme_juridique (methode pure)
# ===========================================================================


class TestGetFormeJuridique:
    def test_sas(self, sirene_tool):
        assert "SAS" in sirene_tool._get_forme_juridique("5720")

    def test_sarl(self, sirene_tool):
        assert "SARL" in sirene_tool._get_forme_juridique("5499")

    def test_entrepreneur_individuel(self, sirene_tool):
        assert "individuel" in sirene_tool._get_forme_juridique("1000").lower()

    def test_unknown_code(self, sirene_tool):
        assert sirene_tool._get_forme_juridique("9999") == "Autre"


# ===========================================================================
# Tests _get_tranche_effectif (methode pure)
# ===========================================================================


class TestGetTrancheEffectif:
    def test_zero_salarie(self, sirene_tool):
        assert "0 salarié" in sirene_tool._get_tranche_effectif("00")

    def test_small(self, sirene_tool):
        assert "1-2" in sirene_tool._get_tranche_effectif("01")

    def test_medium(self, sirene_tool):
        assert "50-99" in sirene_tool._get_tranche_effectif("21")

    def test_large(self, sirene_tool):
        assert "500-999" in sirene_tool._get_tranche_effectif("41")

    def test_very_large(self, sirene_tool):
        assert "10000+" in sirene_tool._get_tranche_effectif("53")

    def test_non_renseigne(self, sirene_tool):
        assert "Non renseigné" in sirene_tool._get_tranche_effectif("NN")

    def test_unknown_code(self, sirene_tool):
        result = sirene_tool._get_tranche_effectif("XX")
        assert "Code XX" in result


# ===========================================================================
# Tests _run - Exception generique
# ===========================================================================


class TestSireneRunGenericException:
    PATCH_TARGET = "wakastart_leads.shared.tools.sirene_tool.requests.get"

    def test_generic_exception(self, sirene_tool, mock_sirene_api_key):
        """Une exception generique (non-requests) est capturee proprement."""
        with patch(self.PATCH_TARGET, side_effect=ValueError("unexpected")):
            result = sirene_tool._run("Google")
            assert "inattendue" in result.lower()
