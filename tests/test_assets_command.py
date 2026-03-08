import tempfile
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
class TestAssetCommands:
    def test_list_empty(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            result = runner.invoke(cli, ["asset", "list"])
            assert result.exit_code == 0
            assert "no assets found" in result.output

    def test_create_and_list(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            result = runner.invoke(cli, [
                "asset", "create",
                "-n", "AAPL", "-d", "Apple Inc.",
                "--class", "equity", "--type", "stock",
                "-q", "100", "-i", "15000", "-c", "17500",
                "--category", "Tech",
            ])
            assert result.exit_code == 0
            assert "AAPL" in result.output
            assert "created" in result.output

            result = runner.invoke(cli, ["asset", "list"])
            assert result.exit_code == 0
            assert "AAPL" in result.output
            assert "equity" in result.output
            assert "15000" in result.output

    def test_edit_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            runner.invoke(cli, [
                "asset", "create", "-n", "GOOG",
                "--class", "equity", "--type", "stock",
                "-q", "50", "-i", "10000", "-c", "12000",
            ])
            result = runner.invoke(cli, [
                "asset", "edit", "1", "-c", "13000",
            ])
            assert result.exit_code == 0
            assert "updated" in result.output

    def test_delete_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            runner.invoke(cli, [
                "asset", "create", "-n", "DEL",
                "--class", "fixed-income", "--type", "bond",
            ])
            result = runner.invoke(cli, ["asset", "delete", "1", "--yes"])
            assert result.exit_code == 0
            assert "deleted" in result.output

            result = runner.invoke(cli, ["asset", "list"])
            assert "no assets found" in result.output

    def test_alias_a_c(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            result = runner.invoke(cli, [
                "a", "c", "-n", "ETF1",
                "--class", "equity", "--type", "etf",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_double_alias_aa(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            runner.invoke(cli, [
                "asset", "create", "-n", "BTC",
                "--class", "equity", "--type", "crypto",
            ])
            result = runner.invoke(cli, ["aa"])
            assert result.exit_code == 0
            assert "BTC" in result.output

    def test_create_with_tags(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            result = runner.invoke(cli, [
                "asset", "create", "-n", "REIT1",
                "--class", "equity", "--type", "reit",
                "-t", "real-estate,income",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_edit_not_found(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            result = runner.invoke(cli, ["asset", "edit", "999", "-n", "X"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_delete_not_found(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session):
            result = runner.invoke(cli, ["asset", "delete", "999", "--yes"])
            assert result.exit_code == 0
            assert "not found" in result.output
