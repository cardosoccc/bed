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
class TestGoalCommands:
    def test_list_empty(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.goals.get_session", session):
            result = runner.invoke(cli, ["goal", "list"])
            assert result.exit_code == 0
            assert "No goals found" in result.output

    def test_create_and_list(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.goals.get_session", session):
            result = runner.invoke(cli, [
                "goal", "create",
                "-d", "Retirement",
                "--class", "current-value",
                "-v", "1000000",
            ])
            assert result.exit_code == 0
            assert "Retirement" in result.output
            assert "created" in result.output

            result = runner.invoke(cli, ["goal", "list"])
            assert result.exit_code == 0
            assert "Retirement" in result.output

    def test_edit_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.goals.get_session", session):
            runner.invoke(cli, [
                "goal", "create", "-d", "Emergency",
                "--class", "invested-value", "-v", "50000",
            ])
            result = runner.invoke(cli, [
                "goal", "edit", "1", "-v", "60000",
            ])
            assert result.exit_code == 0
            assert "updated" in result.output

    def test_delete_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.goals.get_session", session):
            runner.invoke(cli, [
                "goal", "create", "-d", "To Delete",
                "--class", "quantity", "-q", "100",
            ])
            result = runner.invoke(cli, ["goal", "delete", "1", "--yes"])
            assert result.exit_code == 0
            assert "deleted" in result.output

    def test_alias_g_c(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.goals.get_session", session):
            result = runner.invoke(cli, [
                "g", "c", "-d", "Vacation",
                "--class", "invested-value", "-v", "10000",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_double_alias_gg(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.goals.get_session", session):
            runner.invoke(cli, [
                "goal", "create", "-d", "House",
                "--class", "current-value", "-v", "500000",
            ])
            result = runner.invoke(cli, ["gg"])
            assert result.exit_code == 0
            assert "House" in result.output
