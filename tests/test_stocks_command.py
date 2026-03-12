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


def _mock_fetch_prices(tickers):
    return {t: 42.50 for t in tickers}


def _mock_fetch_prices_fail(tickers):
    return {t: None for t in tickers}


@pytest.mark.integration
class TestStocksCommands:
    def test_list_empty(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session):
            result = runner.invoke(cli, ["stocks", "list"])
            assert result.exit_code == 0
            assert "no tickers found" in result.output

    def test_add_and_list(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices):
            result = runner.invoke(cli, ["stocks", "add", "PETR4"])
            assert result.exit_code == 0
            assert "petr4" in result.output
            assert "added" in result.output

            result = runner.invoke(cli, ["stocks", "list"])
            assert result.exit_code == 0
            assert "petr4" in result.output
            assert "42.5" in result.output

    def test_add_invalid_ticker(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices_fail):
            result = runner.invoke(cli, ["stocks", "add", "INVALID123"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_add_duplicate(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["stocks", "add", "VALE3"])
            result = runner.invoke(cli, ["stocks", "add", "VALE3"])
            assert result.exit_code == 0
            assert "already in the list" in result.output

    def test_remove(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["stocks", "add", "BBAS3"])
            result = runner.invoke(cli, ["stocks", "remove", "BBAS3"])
            assert result.exit_code == 0
            assert "removed" in result.output

    def test_remove_not_found(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session):
            result = runner.invoke(cli, ["stocks", "remove", "NOPE"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_update(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["stocks", "add", "PETR4"])
            result = runner.invoke(cli, ["stocks", "update"])
            assert result.exit_code == 0
            assert "updated" in result.output

    def test_list_with_update_flag(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices):
            runner.invoke(cli, ["stocks", "add", "ITUB4"])
            result = runner.invoke(cli, ["stocks", "list", "--update"])
            assert result.exit_code == 0
            assert "updating prices" in result.output
            assert "itub4" in result.output

    def test_alias_s(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session):
            result = runner.invoke(cli, ["s", "l"])
            assert result.exit_code == 0
            assert "no tickers found" in result.output

    def test_alias_ss(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session):
            result = runner.invoke(cli, ["ss"])
            assert result.exit_code == 0
            assert "no tickers found" in result.output

    def test_ticker_lowercase(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.stocks.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices):
            result = runner.invoke(cli, ["stocks", "add", "PETR4"])
            assert result.exit_code == 0
            assert "petr4" in result.output


@pytest.mark.integration
class TestAssetListUpdateFlag:
    def test_asset_list_with_update(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.assets.get_session", session), \
             patch("bed.services.stocks.fetch_prices", _mock_fetch_prices):
            # Create a stock asset first
            runner.invoke(cli, [
                "asset", "create",
                "-n", "petr4", "--class", "equity", "--type", "stock",
                "-q", "100", "-i", "3000", "-c", "3000",
            ])
            result = runner.invoke(cli, ["asset", "list", "--update"])
            assert result.exit_code == 0
            assert "updating stock prices" in result.output
            assert "petr4" in result.output
