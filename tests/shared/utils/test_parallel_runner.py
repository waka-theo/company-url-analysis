"""Tests pour le module parallel_runner."""

import pytest

from wakastart_leads.shared.utils.parallel_runner import RunStatus, UrlResult


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
