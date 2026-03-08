import json
import shutil
from pathlib import Path

import click

from bed.commands.config_store import CONFIG_DIR, DB_PATH, set_config_value, load_config
from bed.commands.db import get_session, run_async
from bed.database import Base
from bed.services.storage import get_provider


SYNC_META_FILE = CONFIG_DIR / "sync_meta.json"


def _load_sync_meta() -> dict:
    if not SYNC_META_FILE.exists():
        return {"version": 0}
    return json.loads(SYNC_META_FILE.read_text())


def _save_sync_meta(meta: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SYNC_META_FILE.write_text(json.dumps(meta, indent=2))


@click.group("portfolio")
def portfolio():
    """Manage the portfolio database."""
    pass


@portfolio.command("init")
def portfolio_init():
    """Initialize a new portfolio database."""

    async def _run():
        async with get_session() as _db:
            pass  # get_session creates tables automatically

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    run_async(_run())
    _save_sync_meta({"version": 0})
    click.echo(f"portfolio initialized at {DB_PATH}")


@portfolio.command("destroy")
@click.confirmation_option(prompt="Are you sure you want to destroy the portfolio?")
def portfolio_destroy():
    """Destroy the portfolio database."""
    if DB_PATH.exists():
        DB_PATH.unlink()
        click.echo("portfolio destroyed.")
    else:
        click.echo("no portfolio found.")


@portfolio.command("push")
@click.option("--force", is_flag=True, help="Force push, overwriting remote.")
def portfolio_push(force):
    """Push the portfolio database to cloud storage."""
    cfg = load_config()
    bucket_url = cfg.get("bucket")
    if not bucket_url:
        click.echo("no bucket configured. use: bed config set bucket s3://... or gs://...")
        return

    if not DB_PATH.exists():
        click.echo("no portfolio database found. run 'bed portfolio init' first.")
        return

    provider = get_provider(bucket_url)
    local_meta = _load_sync_meta()
    remote_meta = provider.read_json("sync_meta.json")

    if remote_meta and not force:
        if remote_meta.get("version", 0) > local_meta.get("version", 0):
            click.echo(
                "remote version is newer. pull first or use --force to overwrite."
            )
            return

    new_version = local_meta.get("version", 0) + 1
    if force and remote_meta:
        new_version = max(local_meta.get("version", 0), remote_meta.get("version", 0)) + 1

    provider.upload(DB_PATH, "bed.db")
    new_meta = {"version": new_version}
    provider.upload_json(new_meta, "sync_meta.json")
    _save_sync_meta(new_meta)
    click.echo(f"portfolio pushed (version {new_version}).")


@portfolio.command("pull")
@click.option("--force", is_flag=True, help="Force pull, overwriting local.")
def portfolio_pull(force):
    """Pull the portfolio database from cloud storage."""
    cfg = load_config()
    bucket_url = cfg.get("bucket")
    if not bucket_url:
        click.echo("no bucket configured. use: bed config set bucket s3://... or gs://...")
        return

    provider = get_provider(bucket_url)
    remote_meta = provider.read_json("sync_meta.json")

    if not remote_meta:
        click.echo("no remote portfolio found.")
        return

    local_meta = _load_sync_meta()
    if not force:
        if local_meta.get("version", 0) > remote_meta.get("version", 0):
            click.echo(
                "local version is newer. push first or use --force to overwrite."
            )
            return

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        backup = DB_PATH.with_suffix(".db.bak")
        shutil.copy2(DB_PATH, backup)
        click.echo(f"backup saved to {backup}")

    provider.download("bed.db", DB_PATH)
    _save_sync_meta(remote_meta)
    click.echo(f"portfolio pulled (version {remote_meta.get('version', 0)}).")
