"""Tests unitaires pour ApolloSearchTool."""

from unittest.mock import patch

import requests

from wakastart_leads.crews.analysis.tools.apollo_tool import ApolloSearchInput


# ===========================================================================
# Tests d'instanciation
# ===========================================================================


class TestApolloToolInstantiation:
    def test_tool_name(self, apollo_tool):
        assert apollo_tool.name == "apollo_search"

    def test_tool_args_schema(self, apollo_tool):
        assert apollo_tool.args_schema is ApolloSearchInput

    def test_seniority_priority_has_expected_keys(self, apollo_tool):
        expected = {"owner", "founder", "c_suite", "vp", "head", "director", "manager"}
        assert set(apollo_tool.SENIORITY_PRIORITY.keys()) == expected

    def test_seniority_priority_ordering(self, apollo_tool):
        p = apollo_tool.SENIORITY_PRIORITY
        assert p["owner"] < p["founder"] < p["c_suite"] < p["vp"] < p["director"]


# ===========================================================================
# Tests _build_linkedin_url
# ===========================================================================


class TestBuildLinkedinUrl:
    def test_none_returns_non_trouve(self, apollo_tool):
        assert apollo_tool._build_linkedin_url(None) == "Non trouve"

    def test_empty_returns_non_trouve(self, apollo_tool):
        assert apollo_tool._build_linkedin_url("") == "Non trouve"

    def test_full_https_url_unchanged(self, apollo_tool):
        url = "https://www.linkedin.com/in/johndoe"
        assert apollo_tool._build_linkedin_url(url) == url

    def test_partial_url_adds_https(self, apollo_tool):
        result = apollo_tool._build_linkedin_url("linkedin.com/in/johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"

    def test_handle_builds_full_url(self, apollo_tool):
        result = apollo_tool._build_linkedin_url("johndoe")
        assert result == "https://www.linkedin.com/in/johndoe"


# ===========================================================================
# Tests _rank_candidates
# ===========================================================================


class TestRankCandidates:
    def test_ceo_before_director(self, apollo_tool):
        """CEO (c_suite) doit etre avant Director."""
        candidates = [
            {"title": "Engineering Director", "has_email": True},
            {"title": "CEO", "has_email": True},
        ]
        result = apollo_tool._rank_candidates(candidates)
        assert result[0]["title"] == "CEO"
        assert result[1]["title"] == "Engineering Director"

    def test_founder_before_vp(self, apollo_tool):
        """Founder doit etre avant VP."""
        candidates = [
            {"title": "VP of Engineering", "has_email": True},
            {"title": "Founder & CEO", "has_email": True},
        ]
        result = apollo_tool._rank_candidates(candidates)
        assert result[0]["title"] == "Founder & CEO"

    def test_cto_ranks_as_c_suite(self, apollo_tool):
        """CTO doit etre classe au meme niveau que C-suite."""
        candidates = [
            {"title": "Head of Marketing", "has_email": True},
            {"title": "CTO", "has_email": True},
        ]
        result = apollo_tool._rank_candidates(candidates)
        assert result[0]["title"] == "CTO"

    def test_has_email_true_preferred(self, apollo_tool):
        """A seniority egale, preferer les candidats avec email."""
        candidates = [
            {"title": "CEO", "has_email": False},
            {"title": "CEO", "has_email": True},
        ]
        result = apollo_tool._rank_candidates(candidates)
        assert result[0]["has_email"] is True

    def test_empty_list(self, apollo_tool):
        assert apollo_tool._rank_candidates([]) == []

    def test_limit_to_3(self, apollo_tool):
        candidates = [{"title": f"CEO {i}", "has_email": True} for i in range(5)]
        result = apollo_tool._rank_candidates(candidates)
        assert len(result) == 3

    def test_unknown_title_last(self, apollo_tool):
        """Titre inconnu doit etre en dernier."""
        candidates = [
            {"title": None, "has_email": True},
            {"title": "Director of Sales", "has_email": True},
        ]
        result = apollo_tool._rank_candidates(candidates)
        assert result[0]["title"] == "Director of Sales"

    def test_french_titles_recognized(self, apollo_tool):
        """Les titres en francais doivent etre reconnus."""
        candidates = [
            {"title": "Responsable Marketing", "has_email": True},
            {"title": "Directeur Technique", "has_email": True},
        ]
        result = apollo_tool._rank_candidates(candidates)
        assert result[0]["title"] == "Directeur Technique"


# ===========================================================================
# Tests _format_decideurs
# ===========================================================================


class TestFormatDecideurs:
    def test_full_data(self, apollo_tool):
        """Formate correctement un contact complet."""
        people = [
            {
                "first_name": "Patrick",
                "last_name": "Collison",
                "title": "CEO",
                "email": "patrick@stripe.com",
                "phone_number": "+1 555 123 4567",
                "linkedin_url": "https://www.linkedin.com/in/patrickcollison",
            }
        ]
        result = apollo_tool._format_decideurs(people, "Stripe")
        assert len(result["decideurs"]) == 3
        d1 = result["decideurs"][0]
        assert d1["nom"] == "Patrick Collison"
        assert d1["titre"] == "CEO"
        assert d1["email"] == "patrick@stripe.com"
        assert d1["telephone"] == "+1 555 123 4567"
        assert d1["linkedin"] == "https://www.linkedin.com/in/patrickcollison"

    def test_missing_fields(self, apollo_tool):
        """Gere les champs manquants avec Non trouve."""
        people = [
            {
                "first_name": "Jean",
                "last_name": None,
                "title": None,
                "email": "jean@test.com",
                "phone_number": None,
                "linkedin_url": None,
            }
        ]
        result = apollo_tool._format_decideurs(people, "TestCo")
        d1 = result["decideurs"][0]
        assert d1["nom"] == "Jean"
        assert d1["titre"] == "Non trouve"
        assert d1["telephone"] == "Non trouve"
        assert d1["linkedin"] == "Non trouve"

    def test_pads_to_3_decideurs(self, apollo_tool):
        """Complete toujours a 3 decideurs."""
        people = [
            {
                "first_name": "Solo",
                "last_name": "Person",
                "title": "CEO",
                "email": "solo@test.com",
                "phone_number": None,
                "linkedin_url": None,
            }
        ]
        result = apollo_tool._format_decideurs(people, "TestCo")
        assert len(result["decideurs"]) == 3
        assert result["decideurs"][0]["nom"] == "Solo Person"
        assert result["decideurs"][1]["nom"] == "Non trouve"
        assert result["decideurs"][2]["nom"] == "Non trouve"

    def test_empty_list(self, apollo_tool):
        """Gere une liste vide de contacts."""
        result = apollo_tool._format_decideurs([], "EmptyCo")
        assert result["contacts_found"] == 0
        assert all(d["nom"] == "Non trouve" for d in result["decideurs"])

    def test_company_in_result(self, apollo_tool):
        """Le nom de l'entreprise est dans le resultat."""
        result = apollo_tool._format_decideurs([], "MyCompany")
        assert result["company"] == "MyCompany"


# ===========================================================================
# Tests _build_search_params
# ===========================================================================


class TestBuildSearchParams:
    def test_with_filters_includes_seniorities(self, apollo_tool):
        params = apollo_tool._build_search_params("stripe.com", with_filters=True)
        param_dict: dict[str, list[str]] = {}
        for key, val in params:
            param_dict.setdefault(key, []).append(val)
        assert param_dict["q_organization_domains_list[]"] == ["stripe.com"]
        assert "c_suite" in param_dict["person_seniorities[]"]
        assert "owner" in param_dict["person_seniorities[]"]
        assert "CTO" in param_dict["person_titles[]"]
        assert param_dict["per_page"] == ["10"]

    def test_without_filters_domain_only(self, apollo_tool):
        params = apollo_tool._build_search_params("stripe.com", with_filters=False)
        param_dict: dict[str, list[str]] = {}
        for key, val in params:
            param_dict.setdefault(key, []).append(val)
        assert param_dict["q_organization_domains_list[]"] == ["stripe.com"]
        assert "person_seniorities[]" not in param_dict
        assert "person_titles[]" not in param_dict
        assert "contact_email_status[]" not in param_dict
        assert param_dict["per_page"] == ["10"]


# ===========================================================================
# Tests _execute_search (mock requests.post)
# ===========================================================================


class TestExecuteSearch:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.apollo_tool.requests.post"

    def test_success_returns_people(self, apollo_tool, mock_apollo_api_key, mock_response, apollo_search_response):
        params = apollo_tool._build_search_params("stripe.com")
        with patch(self.PATCH_TARGET, return_value=mock_response(200, apollo_search_response)):
            result = apollo_tool._execute_search(params)
            assert len(result) == 3
            assert result[0]["first_name"] == "Patrick"

    def test_401_raises_permission_error(self, apollo_tool, mock_apollo_api_key, mock_response):
        params = apollo_tool._build_search_params("stripe.com")
        with patch(self.PATCH_TARGET, return_value=mock_response(401, text="Unauthorized")):
            try:
                apollo_tool._execute_search(params)
                assert False, "Devrait lever PermissionError"
            except PermissionError as e:
                assert "invalide" in str(e)

    def test_403_raises_permission_error(self, apollo_tool, mock_apollo_api_key, mock_response):
        params = apollo_tool._build_search_params("stripe.com")
        with patch(self.PATCH_TARGET, return_value=mock_response(403, text="Forbidden")):
            try:
                apollo_tool._execute_search(params)
                assert False, "Devrait lever PermissionError"
            except PermissionError as e:
                assert "master API key" in str(e)

    def test_429_raises_connection_error(self, apollo_tool, mock_apollo_api_key, mock_response):
        params = apollo_tool._build_search_params("stripe.com")
        with patch(self.PATCH_TARGET, return_value=mock_response(429, text="Too many requests")):
            try:
                apollo_tool._execute_search(params)
                assert False, "Devrait lever ConnectionError"
            except ConnectionError as e:
                assert "Limite" in str(e)


# ===========================================================================
# Tests _search_people (fallback progressif)
# ===========================================================================


class TestSearchPeople:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.apollo_tool.requests.post"

    def test_success_with_filters(self, apollo_tool, mock_apollo_api_key, mock_response, apollo_search_response):
        """Si la recherche filtree retourne des resultats, pas de fallback."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, apollo_search_response)) as mock_post:
            result = apollo_tool._search_people("stripe.com")
            assert len(result) == 3
            assert result[0]["first_name"] == "Patrick"
            # Un seul appel (pas de fallback)
            assert mock_post.call_count == 1

    def test_fallback_when_filtered_empty(self, apollo_tool, mock_apollo_api_key, mock_response, apollo_search_response):
        """Si la recherche filtree retourne 0, fallback sans filtres."""
        empty_resp = mock_response(200, {"total_entries": 0, "people": []})
        full_resp = mock_response(200, apollo_search_response)
        with patch(self.PATCH_TARGET, side_effect=[empty_resp, full_resp]) as mock_post:
            result = apollo_tool._search_people("ai-stroke.com")
            assert len(result) == 3
            # 2 appels : filtre puis fallback
            assert mock_post.call_count == 2
            # Le 2e appel ne doit pas avoir de filtres seniority
            second_call_params = mock_post.call_args_list[1].kwargs.get("params", [])
            param_keys = [k for k, _ in second_call_params]
            assert "person_seniorities[]" not in param_keys

    def test_both_empty_returns_empty(self, apollo_tool, mock_apollo_api_key, mock_response):
        """Si les 2 recherches retournent 0, retourne une liste vide."""
        empty_resp = mock_response(200, {"total_entries": 0, "people": []})
        with patch(self.PATCH_TARGET, return_value=empty_resp) as mock_post:
            result = apollo_tool._search_people("unknown.com")
            assert result == []
            assert mock_post.call_count == 2

    def test_error_on_first_call_propagates(self, apollo_tool, mock_apollo_api_key, mock_response):
        """Les erreurs HTTP sur le premier appel sont propagees (pas de fallback)."""
        with patch(self.PATCH_TARGET, return_value=mock_response(401, text="Unauthorized")):
            try:
                apollo_tool._search_people("stripe.com")
                assert False, "Devrait lever PermissionError"
            except PermissionError as e:
                assert "invalide" in str(e)


# ===========================================================================
# Tests _enrich_person (mock requests.post)
# ===========================================================================


class TestEnrichPerson:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.apollo_tool.requests.post"

    def test_success_returns_person(self, apollo_tool, mock_apollo_api_key, mock_response, apollo_enrich_ceo_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(200, apollo_enrich_ceo_response)):
            result = apollo_tool._enrich_person("apollo-id-001")
            assert result["first_name"] == "Patrick"
            assert result["email"] == "patrick@stripe.com"

    def test_failure_returns_none(self, apollo_tool, mock_apollo_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(404)):
            result = apollo_tool._enrich_person("bad-id")
            assert result is None

    def test_timeout_returns_none(self, apollo_tool, mock_apollo_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.Timeout):
            result = apollo_tool._enrich_person("apollo-id-001")
            assert result is None

    def test_network_error_returns_none(self, apollo_tool, mock_apollo_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError):
            result = apollo_tool._enrich_person("apollo-id-001")
            assert result is None


# ===========================================================================
# Tests _run (integration search + enrich)
# ===========================================================================


class TestApolloRun:
    PATCH_TARGET = "wakastart_leads.crews.analysis.tools.apollo_tool.requests.post"
    VALID_DOMAIN = "stripe.com"
    VALID_COMPANY = "Stripe"

    def test_missing_api_key(self, apollo_tool, clear_all_api_keys):
        result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
        assert "APOLLO_API_KEY non configuree" in result

    def test_success_full_flow(
        self, apollo_tool, mock_apollo_api_key, mock_response,
        apollo_search_response, apollo_enrich_ceo_response,
        apollo_enrich_president_response, apollo_enrich_cto_response,
    ):
        """Test du flux complet : search -> rank -> enrich x3 -> format."""
        enrich_responses = [
            mock_response(200, apollo_enrich_ceo_response),
            mock_response(200, apollo_enrich_president_response),
            mock_response(200, apollo_enrich_cto_response),
        ]
        search_resp = mock_response(200, apollo_search_response)

        with patch(self.PATCH_TARGET, side_effect=[search_resp, *enrich_responses]):
            result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Patrick Collison" in result
            assert "patrick@stripe.com" in result
            assert "CEO" in result or "Co-founder" in result

    def test_no_search_results(
        self, apollo_tool, mock_apollo_api_key, mock_response, apollo_search_empty_response,
    ):
        """Recherche filtree et fallback retournent toutes les 2 vide."""
        with patch(self.PATCH_TARGET, return_value=mock_response(200, apollo_search_empty_response)):
            result = apollo_tool._run("unknown.com", "Unknown")
            assert "Aucun decideur trouve" in result

    def test_search_ok_but_enrich_fails(
        self, apollo_tool, mock_apollo_api_key, mock_response, apollo_search_response,
    ):
        """Search retourne des candidats mais tous les enrichissements echouent."""
        search_resp = mock_response(200, apollo_search_response)
        fail_resp = mock_response(500)

        with patch(self.PATCH_TARGET, side_effect=[search_resp, fail_resp, fail_resp, fail_resp]):
            result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "enrichissement echoue" in result

    def test_partial_enrich(
        self, apollo_tool, mock_apollo_api_key, mock_response,
        apollo_search_response, apollo_enrich_ceo_response,
    ):
        """Seul le premier enrichissement reussit."""
        search_resp = mock_response(200, apollo_search_response)
        fail_resp = mock_response(500)

        with patch(self.PATCH_TARGET, side_effect=[search_resp, mock_response(200, apollo_enrich_ceo_response), fail_resp, fail_resp]):
            result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Patrick Collison" in result
            assert "1 contacts" in result

    def test_http_401(self, apollo_tool, mock_apollo_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(401, text="Unauthorized")):
            result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "invalide" in result

    def test_http_429(self, apollo_tool, mock_apollo_api_key, mock_response):
        with patch(self.PATCH_TARGET, return_value=mock_response(429, text="Too many requests")):
            result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Limite" in result

    def test_timeout(self, apollo_tool, mock_apollo_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.Timeout):
            result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "Timeout" in result

    def test_network_error(self, apollo_tool, mock_apollo_api_key):
        with patch(self.PATCH_TARGET, side_effect=requests.exceptions.ConnectionError("Connection refused")):
            result = apollo_tool._run(self.VALID_DOMAIN, self.VALID_COMPANY)
            assert "connexion" in result.lower()

    def test_sorts_by_seniority(
        self, apollo_tool, mock_apollo_api_key, mock_response,
        apollo_search_needs_ranking_response,
    ):
        """Verifie que CEO est en premier meme s'il est dernier dans la liste de search."""
        enrich_ceo = mock_response(200, {
            "person": {
                "id": "apollo-id-022", "first_name": "Big", "last_name": "Boss",
                "title": "CEO", "email": "ceo@testco.com", "phone_number": None,
                "linkedin_url": "https://www.linkedin.com/in/bigboss",
            }
        })
        enrich_director = mock_response(200, {
            "person": {
                "id": "apollo-id-021", "first_name": "Senior", "last_name": "Manager",
                "title": "Engineering Director", "email": "director@testco.com",
                "phone_number": None, "linkedin_url": None,
            }
        })
        enrich_dev = mock_response(200, {
            "person": {
                "id": "apollo-id-020", "first_name": "Junior", "last_name": "Dev",
                "title": "Software Developer", "email": "dev@testco.com",
                "phone_number": None, "linkedin_url": None,
            }
        })
        search_resp = mock_response(200, apollo_search_needs_ranking_response)

        with patch(self.PATCH_TARGET, side_effect=[search_resp, enrich_ceo, enrich_director, enrich_dev]):
            result = apollo_tool._run("testco.com", "TestCo")
            boss_pos = result.find("Big Boss")
            dev_pos = result.find("Junior Dev")
            assert boss_pos < dev_pos or dev_pos == -1
