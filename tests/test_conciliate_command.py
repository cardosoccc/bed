from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from bed.cli import cli
from bed.commands.db import get_session as real_get_session


def _make_temp_session(db_path: Path):
    url = f"sqlite+aiosqlite:///{db_path}"

    @asynccontextmanager
    async def _session():
        async with real_get_session(url) as session:
            yield session

    return _session


@pytest.fixture
def runner_env(tmp_path):
    db_path = tmp_path / "test.db"
    session_factory = _make_temp_session(db_path)
    runner = CliRunner()
    return runner, session_factory


@pytest.mark.integration
class TestConciliateCommand:
    def test_empty_state(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.conciliate.get_session", session):
            result = runner.invoke(cli, ["conciliate"])
            assert result.exit_code == 0
            assert "no discrepancies" in result.output.lower() or "0 mismatches" in result.output.lower()

    def test_with_matching_data(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.conciliate.get_session", session), \
             patch("bed.commands.transactions.get_session", session), \
             patch("bed.commands.assets.get_session", session):
            # Create a transaction
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-01-15", "-m", "Compra",
                "-p", "PETR4 - PETROBRAS", "-k", "PETR4",
                "-i", "inter", "-q", "100", "-u", "36", "-v", "3600",
            ])
            # Create matching asset
            runner.invoke(cli, [
                "asset", "create",
                "--name", "PETR4", "--class", "equity", "--type", "stock",
                "--quantity", "100",
            ])
            result = runner.invoke(cli, ["conciliate"])
            assert result.exit_code == 0
            assert "0 mismatches" in result.output

    def test_with_mismatch(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.conciliate.get_session", session), \
             patch("bed.commands.transactions.get_session", session), \
             patch("bed.commands.assets.get_session", session):
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-01-15", "-m", "Compra",
                "-p", "PETR4", "-k", "PETR4",
                "-i", "inter", "-q", "300", "-u", "36", "-v", "10800",
            ])
            runner.invoke(cli, [
                "asset", "create",
                "--name", "PETR4", "--class", "equity", "--type", "stock",
                "--quantity", "200",
            ])
            result = runner.invoke(cli, ["conciliate"])
            assert result.exit_code == 0
            assert "mismatch" in result.output.lower()
            assert "PETR4" in result.output

    def test_verbose_shows_matches(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.conciliate.get_session", session), \
             patch("bed.commands.transactions.get_session", session), \
             patch("bed.commands.assets.get_session", session):
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-01-15", "-m", "Compra",
                "-p", "PETR4", "-k", "PETR4",
                "-i", "inter", "-q", "100", "-u", "36", "-v", "3600",
            ])
            runner.invoke(cli, [
                "asset", "create",
                "--name", "PETR4", "--class", "equity", "--type", "stock",
                "--quantity", "100",
            ])
            result = runner.invoke(cli, ["conciliate", "-v"])
            assert result.exit_code == 0
            assert "PETR4" in result.output
            assert "ok" in result.output.lower()

    def test_missing_asset_reported(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.conciliate.get_session", session), \
             patch("bed.commands.transactions.get_session", session):
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-01-15", "-m", "Compra",
                "-p", "CSAN3", "-k", "CSAN3",
                "-i", "inter", "-q", "2600", "-u", "5", "-v", "13000",
            ])
            result = runner.invoke(cli, ["conciliate"])
            assert result.exit_code == 0
            assert "CSAN3" in result.output
            assert "missing" in result.output.lower()
