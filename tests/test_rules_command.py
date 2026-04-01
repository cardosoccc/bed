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
                "--target", "0.30",
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
                "rule", "create", "-d", "Editable Rule", "--target", "20",
            ])
            result = runner.invoke(cli, [
                "rule", "edit", "1", "--target", "25",
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

    def test_create_with_percentage_target(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create",
                "-d", "30% equity",
                "--target", "0.30",
                "--class", "equity",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

            result = runner.invoke(cli, ["rule", "list"])
            assert result.exit_code == 0
            assert "0.30" in result.output
            assert "current" in result.output

    def test_create_with_tags(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create", "-d", "Tag Rule",
                "-t", "defensive,conservative",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_edit_target_rule_to_range(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            runner.invoke(cli, [
                "rule", "create",
                "-d", "Convertible Rule",
                "--target", "0.20",
            ])
            result = runner.invoke(cli, [
                "rule", "edit", "1",
                "--clear-target",
                "--min", "0.10",
                "--max", "0.30",
            ])
            assert result.exit_code == 0
            assert "updated" in result.output

    def test_create_invested_based_rule(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create",
                "-d", "Invested Rule",
                "--target", "5000",
                "--invested",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

            result = runner.invoke(cli, ["rule", "list"])
            assert result.exit_code == 0
            assert "invested" in result.output
            assert "5000.00" in result.output

    def test_create_with_min_and_max(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create",
                "-d", "Range Rule",
                "--min", "0.10",
                "--max", "0.30",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_reject_target_and_min_combination(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create",
                "-d", "Invalid Rule",
                "--target", "0.20",
                "--min", "0.10",
            ])
            assert result.exit_code != 0

    def test_reject_removed_proportion_option(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.rules.get_session", session):
            result = runner.invoke(cli, [
                "rule", "create",
                "-d", "Old Rule",
                "--proportion", "0.30",
            ])
            assert result.exit_code != 0
