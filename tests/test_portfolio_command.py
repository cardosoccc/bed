import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from bed.cli import cli


@pytest.fixture
def runner_env(tmp_path):
    config_dir = tmp_path / ".bed"
    db_path = config_dir / "bed.db"
    config_file = config_dir / "config.json"
    sync_meta_file = config_dir / "sync_meta.json"
    runner = CliRunner()
    return runner, tmp_path, config_dir, db_path, sync_meta_file


@pytest.mark.integration
class TestPortfolioCommands:
    def test_init(self, runner_env):
        runner, tmp_path, config_dir, db_path, sync_meta_file = runner_env
        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.database.DB_URL", f"sqlite+aiosqlite:///{db_path}"),
        ):
            result = runner.invoke(cli, ["portfolio", "init"])
            assert result.exit_code == 0
            assert "initialized" in result.output
            assert sync_meta_file.exists()

    def test_destroy(self, runner_env):
        runner, tmp_path, config_dir, db_path, sync_meta_file = runner_env
        config_dir.mkdir(parents=True, exist_ok=True)
        db_path.touch()

        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
        ):
            result = runner.invoke(cli, ["portfolio", "destroy", "--yes"])
            assert result.exit_code == 0
            assert "destroyed" in result.output or "Destroyed" in result.output
            assert not db_path.exists()

    def test_destroy_no_db(self, runner_env):
        runner, tmp_path, config_dir, db_path, sync_meta_file = runner_env
        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
        ):
            result = runner.invoke(cli, ["portfolio", "destroy", "--yes"])
            assert result.exit_code == 0
            assert "no portfolio found" in result.output

    def test_push_no_bucket(self, runner_env):
        runner, tmp_path, config_dir, db_path, sync_meta_file = runner_env
        config_file = config_dir / "config.json"
        with (
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
        ):
            result = runner.invoke(cli, ["portfolio", "push"])
            assert result.exit_code == 0
            assert "no bucket configured" in result.output

    def test_pull_no_bucket(self, runner_env):
        runner, tmp_path, config_dir, db_path, sync_meta_file = runner_env
        config_file = config_dir / "config.json"
        with (
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
        ):
            result = runner.invoke(cli, ["portfolio", "pull"])
            assert result.exit_code == 0
            assert "no bucket configured" in result.output

    def test_alias_p_init(self, runner_env):
        runner, tmp_path, config_dir, db_path, sync_meta_file = runner_env
        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.database.DB_URL", f"sqlite+aiosqlite:///{db_path}"),
        ):
            result = runner.invoke(cli, ["p", "init"])
            assert result.exit_code == 0
            assert "initialized" in result.output
