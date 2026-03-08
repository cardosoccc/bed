import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from bed.cli import cli


class FakeProvider:
    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.json_store: dict[str, dict] = {}

    def upload(self, local_path: Path, filename: str) -> None:
        self.files[filename] = local_path.read_bytes()

    def download(self, filename: str, local_path: Path) -> None:
        local_path.write_bytes(self.files[filename])

    def read_json(self, filename: str) -> dict | None:
        return self.json_store.get(filename)

    def upload_json(self, data: dict, filename: str) -> None:
        self.json_store[filename] = data


@pytest.fixture
def sync_env(tmp_path):
    config_dir = tmp_path / ".bed"
    config_dir.mkdir()
    db_path = config_dir / "bed.db"
    db_path.write_text("test-db-content")
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"bucket": "s3://test-bucket"}))
    sync_meta_file = config_dir / "sync_meta.json"
    sync_meta_file.write_text(json.dumps({"version": 0}))

    provider = FakeProvider()
    runner = CliRunner()
    return runner, config_dir, db_path, config_file, sync_meta_file, provider


@pytest.mark.integration
class TestSyncCommands:
    def test_push(self, sync_env):
        runner, config_dir, db_path, config_file, sync_meta_file, provider = sync_env
        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
            patch("bed.commands.db_commands.get_provider", return_value=provider),
        ):
            result = runner.invoke(cli, ["portfolio", "push"])
            assert result.exit_code == 0
            assert "pushed" in result.output
            assert "bed.db" in provider.files
            assert provider.json_store["sync_meta.json"]["version"] == 1

    def test_push_conflict(self, sync_env):
        runner, config_dir, db_path, config_file, sync_meta_file, provider = sync_env
        provider.json_store["sync_meta.json"] = {"version": 5}

        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
            patch("bed.commands.db_commands.get_provider", return_value=provider),
        ):
            result = runner.invoke(cli, ["portfolio", "push"])
            assert result.exit_code == 0
            assert "remote version is newer" in result.output

    def test_push_force(self, sync_env):
        runner, config_dir, db_path, config_file, sync_meta_file, provider = sync_env
        provider.json_store["sync_meta.json"] = {"version": 5}

        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
            patch("bed.commands.db_commands.get_provider", return_value=provider),
        ):
            result = runner.invoke(cli, ["portfolio", "push", "--force"])
            assert result.exit_code == 0
            assert "pushed" in result.output
            assert provider.json_store["sync_meta.json"]["version"] == 6

    def test_pull(self, sync_env):
        runner, config_dir, db_path, config_file, sync_meta_file, provider = sync_env
        provider.files["bed.db"] = b"remote-db-content"
        provider.json_store["sync_meta.json"] = {"version": 1}

        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
            patch("bed.commands.db_commands.get_provider", return_value=provider),
        ):
            result = runner.invoke(cli, ["portfolio", "pull"])
            assert result.exit_code == 0
            assert "pulled" in result.output
            assert db_path.read_bytes() == b"remote-db-content"
            backup = db_path.with_suffix(".db.bak")
            assert backup.exists()

    def test_pull_no_remote(self, sync_env):
        runner, config_dir, db_path, config_file, sync_meta_file, provider = sync_env
        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
            patch("bed.commands.db_commands.get_provider", return_value=provider),
        ):
            result = runner.invoke(cli, ["portfolio", "pull"])
            assert result.exit_code == 0
            assert "no remote portfolio found" in result.output

    def test_pull_conflict(self, sync_env):
        runner, config_dir, db_path, config_file, sync_meta_file, provider = sync_env
        sync_meta_file.write_text(json.dumps({"version": 5}))
        provider.json_store["sync_meta.json"] = {"version": 3}

        with (
            patch("bed.commands.db_commands.CONFIG_DIR", config_dir),
            patch("bed.commands.db_commands.DB_PATH", db_path),
            patch("bed.commands.db_commands.SYNC_META_FILE", sync_meta_file),
            patch("bed.commands.config_store.CONFIG_FILE", config_file),
            patch("bed.commands.db_commands.get_provider", return_value=provider),
        ):
            result = runner.invoke(cli, ["portfolio", "pull"])
            assert result.exit_code == 0
            assert "local version is newer" in result.output
