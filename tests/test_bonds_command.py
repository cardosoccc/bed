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


def _mock_fetch_prices():
    return {
        "tesouro selic 2029": 15000.0,
        "tesouro ipca+ 2035": 3200.0,
        "tesouro prefixado 2027": 800.0,
    }


def _mock_fetch_prices_empty():
    return {}


@pytest.mark.integration
class TestBondsCommands:
    def test_list_empty(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session):
            result = runner.invoke(cli, ["bonds", "list"])
            assert result.exit_code == 0
            assert "no bonds found" in result.output

    def test_add_and_list(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            result = runner.invoke(cli, ["bonds", "add", "tesouro", "selic", "2029"])
            assert result.exit_code == 0
            assert "tesouro selic 2029" in result.output
            assert "added" in result.output

            result = runner.invoke(cli, ["bonds", "list"])
            assert result.exit_code == 0
            assert "tesouro selic 2029" in result.output
            assert "15000" in result.output

    def test_add_api_failure(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices_empty):
            result = runner.invoke(cli, ["bonds", "add", "tesouro", "selic", "2029"])
            assert result.exit_code == 0
            assert "failed to fetch" in result.output

    def test_add_no_match(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            result = runner.invoke(cli, ["bonds", "add", "nonexistent", "bond"])
            assert result.exit_code == 0
            assert "no bonds matching" in result.output

    def test_add_duplicate(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["bonds", "add", "tesouro", "selic", "2029"])
            result = runner.invoke(cli, ["bonds", "add", "tesouro", "selic", "2029"])
            assert result.exit_code == 0
            assert "already in the list" in result.output

    def test_add_partial_match_single(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", lambda: {"tesouro prefixado 2027": 800.0}):
            result = runner.invoke(cli, ["bonds", "add", "prefixado"])
            assert result.exit_code == 0
            assert "tesouro prefixado 2027" in result.output
            assert "added" in result.output

    def test_add_partial_match_multiple(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            result = runner.invoke(cli, ["bonds", "add", "tesouro"])
            assert result.exit_code == 0
            assert "multiple bonds match" in result.output

    def test_remove(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["bonds", "add", "tesouro", "selic", "2029"])
            result = runner.invoke(cli, ["bonds", "remove", "tesouro", "selic", "2029"])
            assert result.exit_code == 0
            assert "removed" in result.output

    def test_remove_not_found(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session):
            result = runner.invoke(cli, ["bonds", "remove", "nope"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_update(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["bonds", "add", "tesouro", "selic", "2029"])
            result = runner.invoke(cli, ["bonds", "update"])
            assert result.exit_code == 0
            assert "updated" in result.output

    def test_list_with_update_flag(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["bonds", "add", "tesouro", "selic", "2029"])
            result = runner.invoke(cli, ["bonds", "list", "--update"])
            assert result.exit_code == 0
            assert "updating prices" in result.output
            assert "tesouro selic 2029" in result.output

    def test_search(self, runner_env):
        runner, session = runner_env
        with patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            result = runner.invoke(cli, ["bonds", "search", "selic"])
            assert result.exit_code == 0
            assert "tesouro selic 2029" in result.output

    def test_search_no_results(self, runner_env):
        runner, session = runner_env
        with patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            result = runner.invoke(cli, ["bonds", "search", "nonexistent"])
            assert result.exit_code == 0
            assert "no bonds matching" in result.output

    def test_search_api_failure(self, runner_env):
        runner, session = runner_env
        with patch("bed.services.bonds.fetch_prices", _mock_fetch_prices_empty):
            result = runner.invoke(cli, ["bonds", "search", "selic"])
            assert result.exit_code == 0
            assert "failed to fetch" in result.output

    def test_alias_b(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session):
            result = runner.invoke(cli, ["b", "l"])
            assert result.exit_code == 0
            assert "no bonds found" in result.output

    def test_alias_bb(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.bonds.get_session", session):
            result = runner.invoke(cli, ["bb"])
            assert result.exit_code == 0
            assert "no bonds found" in result.output


@pytest.mark.integration
class TestAssetListBondUpdateFlag:
    def test_asset_list_with_update(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session), \
             patch("bed.services.stocks.fetch_prices", lambda tickers: {}), \
             patch("bed.services.bonds.fetch_prices", _mock_fetch_prices):
            # Create a bond asset first
            create_result = runner.invoke(cli, [
                "asset", "create",
                "-n", "tesouro selic 2029", "--class", "fixed-income", "--type", "bond",
                "-q", "1", "-i", "10000", "-c", "10000",
            ])
            assert create_result.exit_code == 0, create_result.output

            result = runner.invoke(cli, ["asset", "list", "--update"])
            assert result.exit_code == 0
            assert "updating bond prices" in result.output
            assert "tesouro selic 2029" in result.output
