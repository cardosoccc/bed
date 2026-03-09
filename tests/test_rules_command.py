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
class TestRuleCommands:
    def test_list_empty(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, ["rule", "list"])
            assert result.exit_code == 0
            assert "no rules found" in result.output

    def test_create_and_list(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create",
                "-d", "Max 30% equity",
                "--class", "equity",
                "-c", "30",
            ])
            assert result.exit_code == 0
            assert "Max 30% equity" in result.output
            assert "created" in result.output

            result = runner.invoke(cli, ["rule", "list"])
            assert result.exit_code == 0
            assert "Max 30% equity" in result.output

    def test_edit_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            runner.invoke(cli, [
                "rule", "create", "-d", "Editable Rule", "-c", "20",
            ])
            result = runner.invoke(cli, [
                "rule", "edit", "1", "-c", "25",
            ])
            assert result.exit_code == 0
            assert "updated" in result.output

    def test_delete_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            runner.invoke(cli, [
                "rule", "create", "-d", "To Delete",
            ])
            result = runner.invoke(cli, ["rule", "delete", "1", "--yes"])
            assert result.exit_code == 0
            assert "deleted" in result.output

    def test_alias_r_c(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "r", "c", "-d", "New Rule", "--type", "stock",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_double_alias_rr(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            runner.invoke(cli, [
                "rule", "create", "-d", "Listed Rule",
            ])
            result = runner.invoke(cli, ["rr"])
            assert result.exit_code == 0
            assert "Listed Rule" in result.output

    def test_create_with_proportion(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create",
                "-d", "30% equity",
                "-p", "0.30",
                "--class", "equity",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

            result = runner.invoke(cli, ["rule", "list"])
            assert result.exit_code == 0
            assert "30.00%" in result.output

    def test_create_with_tags(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create", "-d", "Tag Rule",
                "-t", "defensive,conservative",
            ])
            assert result.exit_code == 0
            assert "created" in result.output
