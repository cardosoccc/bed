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


def _create_asset(runner, cli, name, asset_class, asset_type, initial, current,
                  category=None, tags=None):
    args = [
        "asset", "create",
        "-n", name,
        "--class", asset_class,
        "--type", asset_type,
        "-q", "1",
        "-i", str(initial),
        "-c", str(current),
    ]
    if category:
        args.extend(["--category", category])
    if tags:
        args.extend(["-t", tags])
    return runner.invoke(cli, args)


def _create_rule(runner, cli, description, proportion=None, asset_class=None, tags=None,
                 min_proportion=None, max_proportion=None):
    args = ["rule", "create", "-d", description]
    if proportion is not None:
        args.extend(["-p", str(proportion)])
    if min_proportion is not None:
        args.extend(["--min-proportion", str(min_proportion)])
    if max_proportion is not None:
        args.extend(["--max-proportion", str(max_proportion)])
    if asset_class:
        args.extend(["--class", asset_class])
    if tags:
        args.extend(["-t", tags])
    return runner.invoke(cli, args)


@pytest.mark.integration
class TestPortfolioStatus:
    def test_status_empty(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
        ):
            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            assert "no assets found" in result.output

    def test_status_with_assets(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
        ):
            _create_asset(runner, cli, "AAPL", "equity", "stock", 10000, 12000)
            _create_asset(runner, cli, "GOVT", "fixed-income", "bond", 5000, 5200)

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            assert "Assets" in result.output
            assert "AAPL" in result.output
            assert "GOVT" in result.output
            assert "TOTAL" in result.output
            assert "15000.00" in result.output  # total initial
            assert "17200.00" in result.output  # total current
            assert "Classes" in result.output
            assert "equity" in result.output
            assert "fixed-income" in result.output

    def test_status_class_percentages(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 7000, 8000)
            _create_asset(runner, cli, "Bond1", "fixed-income", "bond", 2000, 2000)

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            # equity is 8000/10000 = 80%
            assert "80.00%" in result.output
            # fixed-income is 2000/10000 = 20%
            assert "20.00%" in result.output

    def test_status_with_class_rules(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
            patch("bed.commands.rules.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 7000, 8000)
            _create_asset(runner, cli, "Bond1", "fixed-income", "bond", 2000, 2000)

            _create_rule(runner, cli, "60% equity", proportion=0.60, asset_class="equity")
            _create_rule(runner, cli, "40% bonds", proportion=0.40, asset_class="fixed-income")

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            # equity target = 10000 * 60% = 6000
            assert "6000.00" in result.output
            # equity diff = 8000 - 6000 = 2000
            assert "2000.00" in result.output
            # fixed-income target = 10000 * 40% = 4000
            assert "4000.00" in result.output
            # fixed-income diff = 2000 - 4000 = -2000
            assert "-2000.00" in result.output
            # target pct
            assert "60.00%" in result.output
            assert "40.00%" in result.output

    def test_status_with_tags(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
            patch("bed.commands.rules.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 5000, 6000, tags="growth,us")
            _create_asset(runner, cli, "Bond1", "fixed-income", "bond", 3000, 4000, tags="defensive")

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            assert "Tags" in result.output
            assert "growth" in result.output
            assert "us" in result.output
            assert "defensive" in result.output

    def test_status_with_tag_rules(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
            patch("bed.commands.rules.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 5000, 6000, tags="growth")
            _create_asset(runner, cli, "Bond1", "fixed-income", "bond", 4000, 4000, tags="defensive")

            _create_rule(runner, cli, "50% growth", proportion=0.50, tags="growth")
            _create_rule(runner, cli, "50% defensive", proportion=0.50, tags="defensive")

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            # growth: total=6000, target=10000*50%=5000, diff=1000
            assert "5000.00" in result.output
            assert "1000.00" in result.output

    def test_status_with_min_max_within_band(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
            patch("bed.commands.rules.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 7000, 6000)
            _create_asset(runner, cli, "Bond1", "fixed-income", "bond", 3000, 4000)

            _create_rule(runner, cli, "equity band", proportion=0.60,
                         min_proportion=0.50, max_proportion=0.70,
                         asset_class="equity")

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            # equity total=6000, min=5000, max=7000 → within band → diff=0
            assert "0.00" in result.output

    def test_status_with_min_max_below_band(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
            patch("bed.commands.rules.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 4000, 4000)
            _create_asset(runner, cli, "Bond1", "fixed-income", "bond", 6000, 6000)

            _create_rule(runner, cli, "equity band", proportion=0.60,
                         min_proportion=0.50, max_proportion=0.70,
                         asset_class="equity")

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            # equity total=4000, min=5000 → diff = 4000-5000 = -1000
            assert "-1000.00" in result.output

    def test_status_no_tags(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 5000, 6000)

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            assert "no tags found" in result.output

    def test_status_separator_width(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 5000, 6000)

            result = runner.invoke(cli, ["portfolio", "status"])
            assert result.exit_code == 0
            lines = result.output.split("\n")
            separator_lines = [l for l in lines if l.startswith("─")]
            assert len(separator_lines) >= 3
            for sep in separator_lines:
                assert len(sep) == 120

    def test_alias_p_status(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 5000, 6000)

            result = runner.invoke(cli, ["p", "s"])
            assert result.exit_code == 0
            assert "Assets" in result.output

    def test_alias_pp(self, runner_env):
        runner, session = runner_env
        with (
            patch("bed.commands.db_commands.get_session", session),
            patch("bed.commands.assets.get_session", session),
        ):
            _create_asset(runner, cli, "Stock1", "equity", "stock", 5000, 6000)

            result = runner.invoke(cli, ["pp"])
            assert result.exit_code == 0
            assert "Assets" in result.output
