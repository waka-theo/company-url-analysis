"""Tests pour le module parallel_runner."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from wakastart_leads.shared.utils.parallel_runner import (
    RunStatus,
    UrlResult,
    append_result_to_csv,
    clean_csv_row,
    merge_results_to_csv,
    run_sequential,
    run_single_url,
)


class TestCleanCsvRow:
    """Tests pour la fonction clean_csv_row."""

    def test_removes_markdown_backticks(self):
        """Supprime les backticks markdown."""
        raw = "```csv Entreprise,https://example.com,FR ```"
        result = clean_csv_row(raw)
        assert "```" not in result
        assert "Entreprise" in result

    def test_removes_header_keeps_data(self):
        """Supprime le header répété et garde les données."""
        raw = (
            "Société,Site Web,Nationalité,Année Création,Solution SaaS,"
            "Pertinence (%),Stratégie & Angle,Décideur 1 - Nom,Décideur 1 - Titre,"
            "Décideur 1 - Email,Décideur 1 - Téléphone,Décideur 1 - LinkedIn,"
            "Décideur 2 - Nom,Décideur 2 - Titre,Décideur 2 - Email,"
            "Décideur 2 - Téléphone,Décideur 2 - LinkedIn,Décideur 3 - Nom,"
            "Décideur 3 - Titre,Décideur 3 - Email,Décideur 3 - Téléphone,"
            "Décideur 3 - LinkedIn,Page Gamma "
            '"MonEntreprise","https://example.com","FR","2020"'
        )
        result = clean_csv_row(raw)
        assert result is not None
        assert "MonEntreprise" in result

    def test_returns_none_for_empty(self):
        """Retourne None pour une chaîne vide."""
        assert clean_csv_row("") is None
        assert clean_csv_row("   ") is None
        assert clean_csv_row(None) is None

    def test_removes_multiple_backtick_styles(self):
        """Supprime différents styles de backticks."""
        cases = [
            "``` data,here ```",
            "```csv data,here ```",
            "```CSV data,here```",
        ]
        for raw in cases:
            result = clean_csv_row(raw)
            assert "```" not in result
            assert "data" in result

    def test_cleans_real_agent_output(self):
        """Nettoie une sortie réelle d'agent LLM."""
        raw = (
            '``` Société,Site Web,Nationalité,Année Création,Solution SaaS,'
            'Pertinence (%),Stratégie & Angle,Décideur 1 - Nom,Décideur 1 - Titre,'
            'Décideur 1 - Email,Décideur 1 - Téléphone,Décideur 1 - LinkedIn,'
            'Décideur 2 - Nom,Décideur 2 - Titre,Décideur 2 - Email,'
            'Décideur 2 - Téléphone,Décideur 2 - LinkedIn,Décideur 3 - Nom,'
            'Décideur 3 - Titre,Décideur 3 - Email,Décideur 3 - Téléphone,'
            'Décideur 3 - LinkedIn,Page Gamma '
            '"Faks","https://faks.co","FR","2020","SaaS pharma","70%",'
            '"Angle HDS","John Doe","CEO","john@faks.co","","linkedin.com/in/john",'
            '"","","","","","","","","","","https://gamma.app/xxx" ```'
        )
        result = clean_csv_row(raw)
        assert result is not None
        assert "```" not in result
        assert "Faks" in result
        assert "https://faks.co" in result


class TestRunStatus:
    """Tests pour l'enum RunStatus."""

    def test_status_values(self):
        """Vérifie les valeurs des statuts."""
        assert RunStatus.SUCCESS.value == "success"
        assert RunStatus.FAILED.value == "failed"
        assert RunStatus.TIMEOUT.value == "timeout"


class TestUrlResult:
    """Tests pour la dataclass UrlResult."""

    def test_create_success_result(self):
        """Crée un résultat de succès."""
        result = UrlResult(
            url="https://example.com",
            status=RunStatus.SUCCESS,
            csv_row="Example,https://example.com,FR,2020",
            error=None,
            duration_seconds=15.5,
        )
        assert result.url == "https://example.com"
        assert result.status == RunStatus.SUCCESS
        assert result.csv_row is not None
        assert result.error is None

    def test_create_failed_result(self):
        """Crée un résultat d'échec."""
        result = UrlResult(
            url="https://broken.com",
            status=RunStatus.FAILED,
            csv_row=None,
            error="Connection timeout",
            duration_seconds=30.0,
        )
        assert result.status == RunStatus.FAILED
        assert result.csv_row is None
        assert "timeout" in result.error.lower()


class TestRunSingleUrl:
    """Tests pour la fonction run_single_url."""

    async def test_success_execution(self, tmp_path):
        """Test exécution réussie d'une URL."""
        mock_crew_class = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance
        mock_crew_instance.crew.return_value.kickoff.return_value = MagicMock(raw="CSV,row,data")

        result = await run_single_url(
            url="https://example.com",
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            timeout=60,
        )

        assert result.status == RunStatus.SUCCESS
        assert result.csv_row == "CSV,row,data"
        assert result.error is None

    async def test_timeout_execution(self, tmp_path):
        """Test timeout d'une URL."""
        mock_crew_class = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew_class.return_value = mock_crew_instance

        async def slow_to_thread(*args, **kwargs):
            await asyncio.sleep(10)
            return MagicMock(raw="data")

        with patch(
            "wakastart_leads.shared.utils.parallel_runner.asyncio.to_thread",
            side_effect=slow_to_thread,
        ):
            result = await run_single_url(
                url="https://slow.com",
                crew_class=mock_crew_class,
                log_dir=tmp_path,
                timeout=1,
            )

        assert result.status == RunStatus.TIMEOUT
        assert "timeout" in result.error.lower()

    async def test_exception_execution(self, tmp_path):
        """Test exception durant l'exécution."""
        mock_crew_class = MagicMock()
        mock_crew_class.return_value.crew.return_value.kickoff.side_effect = Exception("API Error")

        result = await run_single_url(
            url="https://error.com",
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            timeout=60,
        )

        assert result.status == RunStatus.FAILED
        assert "API Error" in result.error


class TestRunParallel:
    """Tests pour la fonction run_parallel."""

    @pytest.mark.asyncio
    async def test_parallel_with_semaphore(self, tmp_path):
        """Test limitation du nombre de workers."""
        from wakastart_leads.shared.utils.parallel_runner import run_parallel

        mock_crew_class = MagicMock()

        def create_mock_instance():
            instance = MagicMock()
            instance.crew.return_value.kickoff.return_value = MagicMock(raw="data")
            return instance

        mock_crew_class.side_effect = create_mock_instance

        urls = ["https://a.com", "https://b.com", "https://c.com", "https://d.com"]

        results = await run_parallel(
            urls=urls,
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            max_workers=2,
            timeout=60,
            retry_count=0,
        )

        assert len(results) == 4
        success_count = sum(1 for r in results if r.status == RunStatus.SUCCESS)
        assert success_count == 4

    @pytest.mark.asyncio
    async def test_parallel_one_failure_continues(self, tmp_path):
        """Test que les autres URLs continuent si une echoue."""
        from wakastart_leads.shared.utils.parallel_runner import run_parallel

        call_count = [0]

        def create_mock_instance():
            call_count[0] += 1
            instance = MagicMock()
            if call_count[0] == 2:
                instance.crew.return_value.kickoff.side_effect = Exception("Error on URL 2")
            else:
                instance.crew.return_value.kickoff.return_value = MagicMock(raw="data")
            return instance

        mock_crew_class = MagicMock(side_effect=create_mock_instance)

        urls = ["https://a.com", "https://b.com", "https://c.com"]

        results = await run_parallel(
            urls=urls,
            crew_class=mock_crew_class,
            log_dir=tmp_path,
            max_workers=1,
            timeout=60,
            retry_count=0,
        )

        assert len(results) == 3
        success_count = sum(1 for r in results if r.status == RunStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == RunStatus.FAILED)
        assert success_count == 2
        assert failed_count == 1


class TestMergeResultsToCsv:
    """Tests pour la fonction merge_results_to_csv."""

    def test_merge_success_only(self, tmp_path):
        """Fusionne uniquement les résultats réussis."""
        results = [
            UrlResult("https://a.com", RunStatus.SUCCESS, "A,https://a.com,FR", None, 10),
            UrlResult("https://b.com", RunStatus.FAILED, None, "error", 5),
            UrlResult("https://c.com", RunStatus.SUCCESS, "C,https://c.com,US", None, 15),
        ]

        output = tmp_path / "report.csv"
        backup_dir = tmp_path / "backups"

        merge_results_to_csv(results, output, backup_dir)

        assert output.exists()
        content = output.read_text()
        assert "A,https://a.com,FR" in content
        assert "C,https://c.com,US" in content
        assert "error" not in content

    def test_merge_creates_backup(self, tmp_path):
        """Crée un backup si le fichier existe déjà."""
        output = tmp_path / "report.csv"
        backup_dir = tmp_path / "backups"

        # Créer un fichier existant
        output.write_text("OLD,DATA")

        results = [
            UrlResult("https://new.com", RunStatus.SUCCESS, "NEW,DATA", None, 10),
        ]

        merge_results_to_csv(results, output, backup_dir)

        # Vérifier le backup
        assert backup_dir.exists()
        backups = list(backup_dir.glob("*.csv"))
        assert len(backups) == 1
        assert "OLD,DATA" in backups[0].read_text()

        # Vérifier le nouveau contenu
        assert "NEW,DATA" in output.read_text()

    def test_merge_empty_results(self, tmp_path):
        """Gère une liste de résultats vide."""
        results = []
        output = tmp_path / "report.csv"
        backup_dir = tmp_path / "backups"

        merge_results_to_csv(results, output, backup_dir)

        assert output.exists()
        # Fichier avec header uniquement
        content = output.read_text()
        assert "Societe" in content  # Header présent


class TestAppendResultToCsv:
    """Tests pour la fonction append_result_to_csv."""

    def test_append_creates_file_with_header(self, tmp_path):
        """Crée le fichier avec header s'il n'existe pas."""
        output = tmp_path / "report.csv"
        result = UrlResult("https://a.com", RunStatus.SUCCESS, "A,data", None, 10)

        append_result_to_csv(result, output)

        assert output.exists()
        content = output.read_text()
        assert "Societe" in content  # Header
        assert "A,data" in content  # Data

    def test_append_adds_to_existing(self, tmp_path):
        """Ajoute au fichier existant sans recréer le header."""
        output = tmp_path / "report.csv"
        # Créer le fichier avec header + une ligne
        output.write_text("Societe,Site Web\nFirst,data\n", encoding="utf-8-sig")

        result = UrlResult("https://b.com", RunStatus.SUCCESS, "Second,data", None, 10)
        append_result_to_csv(result, output)

        content = output.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3  # Header + 2 lignes de données
        assert "Second,data" in content

    def test_append_ignores_failed_results(self, tmp_path):
        """N'ajoute pas les résultats en échec."""
        output = tmp_path / "report.csv"
        result = UrlResult("https://fail.com", RunStatus.FAILED, None, "error", 10)

        append_result_to_csv(result, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8-sig")  # UTF-8 BOM aware
        assert "error" not in content
        # Seulement le header
        assert "Societe" in content


class TestRunSequential:
    """Tests pour la fonction run_sequential."""

    @pytest.mark.asyncio
    async def test_sequential_processes_in_order(self, tmp_path):
        """Traite les URLs dans l'ordre."""
        mock_crew_class = MagicMock()
        call_order = []

        def create_mock_instance():
            instance = MagicMock()

            def record_call(*args, **kwargs):
                url = kwargs.get("inputs", {}).get("url", "unknown")
                call_order.append(url)
                return MagicMock(raw=f"data-{url}")

            instance.crew.return_value.kickoff.side_effect = record_call
            return instance

        mock_crew_class.side_effect = create_mock_instance

        urls = ["https://first.com", "https://second.com", "https://third.com"]
        output = tmp_path / "report.csv"

        await run_sequential(
            urls=urls,
            crew_class=mock_crew_class,
            log_dir=tmp_path / "logs",
            output_path=output,
            timeout=60,
            retry_count=0,
        )

        # Vérifie l'ordre
        assert call_order == urls

    @pytest.mark.asyncio
    async def test_sequential_saves_after_each(self, tmp_path):
        """Sauvegarde après chaque URL."""
        mock_crew_class = MagicMock()
        save_counts = []

        def create_mock_instance():
            instance = MagicMock()
            instance.crew.return_value.kickoff.return_value = MagicMock(raw="row,data")
            return instance

        mock_crew_class.side_effect = create_mock_instance

        output = tmp_path / "report.csv"

        # Wrapper pour compter les lignes après chaque append
        original_append = append_result_to_csv

        def counting_append(result, path):
            original_append(result, path)
            if path.exists():
                lines = path.read_text().strip().split("\n")
                save_counts.append(len(lines) - 1)  # -1 pour le header

        with patch(
            "wakastart_leads.shared.utils.parallel_runner.append_result_to_csv",
            side_effect=counting_append,
        ):
            await run_sequential(
                urls=["https://a.com", "https://b.com"],
                crew_class=mock_crew_class,
                log_dir=tmp_path / "logs",
                output_path=output,
                timeout=60,
                retry_count=0,
            )

        # Après chaque URL, le compteur augmente
        assert save_counts == [1, 2]
