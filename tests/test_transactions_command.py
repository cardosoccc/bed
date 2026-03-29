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
class TestTransactionCommands:
    def test_list_empty(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, ["transaction", "list"])
            assert result.exit_code == 0
            assert "no transactions found" in result.output

    def test_create_and_list(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-03-26",
                "-m", "Compra",
                "-p", "PETR4 - PETROBRAS",
                "-k", "PETR4",
                "-i", "inter",
                "-q", "100",
                "-u", "46.00",
                "-v", "4600.00",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

            result = runner.invoke(cli, ["transaction", "list"])
            assert result.exit_code == 0
            assert "PETR4" in result.output
            assert "Compra" in result.output
            assert "inter" in result.output

    def test_create_with_tags(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-03-26",
                "-m", "Dividendo",
                "-p", "VALE3 - VALE",
                "-i", "btg-pactual",
                "-t", "energia,mineração",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_edit_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-03-26", "-m", "Compra",
                "-p", "PETR4", "-i", "inter",
            ])
            result = runner.invoke(cli, [
                "transaction", "edit", "1", "-v", "5000",
            ])
            assert result.exit_code == 0
            assert "updated" in result.output

    def test_delete_by_number(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-03-26", "-m", "Compra",
                "-p", "DEL", "-i", "inter",
            ])
            result = runner.invoke(cli, ["transaction", "delete", "1", "--yes"])
            assert result.exit_code == 0
            assert "deleted" in result.output

            result = runner.invoke(cli, ["transaction", "list"])
            assert "no transactions found" in result.output

    def test_edit_not_found(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, ["transaction", "edit", "999", "-m", "Venda"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_delete_not_found(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, ["transaction", "delete", "999", "--yes"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_alias_t_c(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "t", "c",
                "-d", "2026-03-26", "-m", "Compra",
                "-p", "VALE3", "-i", "inter",
            ])
            assert result.exit_code == 0
            assert "created" in result.output

    def test_double_alias_tt(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-03-26", "-m", "Compra",
                "-p", "BTC", "-i", "inter",
            ])
            result = runner.invoke(cli, ["tt"])
            assert result.exit_code == 0
            assert "BTC" in result.output

    def test_bare_transaction_invokes_list(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, ["transaction"])
            assert result.exit_code == 0
            assert "no transactions found" in result.output

    def test_list_with_filters(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-01-15", "-m", "Compra",
                "-p", "PETR4", "-k", "PETR4", "-i", "inter",
            ])
            runner.invoke(cli, [
                "transaction", "create",
                "-d", "2026-03-20", "-m", "Dividendo",
                "-p", "VALE3", "-k", "VALE3", "-i", "btg-pactual",
            ])

            # Filter by ticker
            result = runner.invoke(cli, ["transaction", "list", "-k", "PETR4"])
            assert result.exit_code == 0
            assert "PETR4" in result.output
            assert "VALE3" not in result.output

            # Filter by date range
            result = runner.invoke(cli, ["transaction", "list", "-f", "2026-03-01"])
            assert result.exit_code == 0
            assert "VALE3" in result.output
            assert "PETR4" not in result.output


@pytest.mark.integration
class TestImportCommand:
    def test_no_source_flag_shows_error(self, runner_env):
        runner, session = runner_env
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, ["transaction", "import"])
            assert result.exit_code != 0 or "specify one" in result.output.lower() or "error" in result.output.lower()

    def test_multiple_source_flags_shows_error(self, runner_env, tmp_path):
        runner, session = runner_env
        f = tmp_path / "dummy.xlsx"
        f.touch()
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "import",
                "--agf", str(f), "--neg", str(f),
            ])
            assert result.exit_code != 0 or "specify one" in result.output.lower() or "mutually exclusive" in result.output.lower()

    def test_import_neg_dry_run(self, runner_env):
        runner, session = runner_env
        neg_file = str(Path(__file__).parent.parent / "negociacao-2026-03-29-01-28-10.xlsx")
        if not Path(neg_file).exists():
            pytest.skip("negociacao file not available")
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "import", "--neg", neg_file, "--dry-run",
            ])
            assert result.exit_code == 0
            assert "dry-run" in result.output.lower()
            assert "would import" in result.output.lower()

    def test_import_mov_dry_run(self, runner_env):
        runner, session = runner_env
        mov_file = str(Path(__file__).parent.parent / "movimentacao-2026-03-28-16-48-38.xlsx")
        if not Path(mov_file).exists():
            pytest.skip("movimentacao file not available")
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "import", "--mov", mov_file, "--dry-run",
            ])
            assert result.exit_code == 0
            assert "dry-run" in result.output.lower()
            assert "would import" in result.output.lower()

    def test_import_agf_dry_run(self, runner_env):
        runner, session = runner_env
        agf_file = str(Path(__file__).parent.parent / "agf.xlsx")
        if not Path(agf_file).exists():
            pytest.skip("agf file not available")
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "import", "--agf", agf_file, "--dry-run",
            ])
            assert result.exit_code == 0
            assert "dry-run" in result.output.lower()
            assert "would import" in result.output.lower()

    def test_import_agf_with_institution(self, runner_env):
        runner, session = runner_env
        agf_file = str(Path(__file__).parent.parent / "agf.xlsx")
        if not Path(agf_file).exists():
            pytest.skip("agf file not available")
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "import", "--agf", agf_file,
                "--institution", "btg-pactual", "--dry-run",
            ])
            assert result.exit_code == 0
            assert "dry-run" in result.output.lower()

    def test_import_neg_creates_transactions(self, runner_env):
        runner, session = runner_env
        neg_file = str(Path(__file__).parent.parent / "negociacao-2026-03-29-01-28-10.xlsx")
        if not Path(neg_file).exists():
            pytest.skip("negociacao file not available")
        with patch("bed.commands.transactions.get_session", session):
            result = runner.invoke(cli, [
                "transaction", "import", "--neg", neg_file,
            ])
            assert result.exit_code == 0
            assert "imported" in result.output

    def test_import_neg_dedup(self, runner_env):
        runner, session = runner_env
        neg_file = str(Path(__file__).parent.parent / "negociacao-2026-03-29-01-28-10.xlsx")
        if not Path(neg_file).exists():
            pytest.skip("negociacao file not available")
        with patch("bed.commands.transactions.get_session", session):
            # First import
            runner.invoke(cli, ["transaction", "import", "--neg", neg_file])
            # Second import - all should be skipped
            result = runner.invoke(cli, ["transaction", "import", "--neg", neg_file])
            assert result.exit_code == 0
            assert "0 imported" in result.output
