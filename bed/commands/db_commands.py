import json
import shutil
from pathlib import Path

import click
from tabulate import tabulate

from bed.commands.config_store import CONFIG_DIR, DB_PATH, set_config_value, load_config
from bed.commands.db import get_session, run_async
from bed.database import Base
from bed.services.portfolio import get_portfolio_status
from bed.services.storage import get_provider


TABLE_WIDTH = 120


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


@portfolio.command("status")
def portfolio_status():
    """Show current portfolio status report."""

    async def _run():
        async with get_session() as db:
            return await get_portfolio_status(db)

    status = run_async(_run())

    if not status.assets:
        click.echo("no assets found.")
        return

    separator = "─" * TABLE_WIDTH

    # --- Table 1: Assets ---
    click.echo(separator)
    click.echo("Assets")
    click.echo(separator)
    asset_headers = ["#", "name", "class", "type", "qty", "initial", "current", "category", "subcat", "tags"]
    asset_colalign = ("right", "left", "left", "left", "right", "right", "right", "left", "left", "left")
    rows = []
    for i, a in enumerate(status.assets, 1):
        rows.append([
            i,
            a.name,
            a.asset_class.value if a.asset_class else "",
            a.asset_type.value if a.asset_type else "",
            f"{a.quantity:.4f}",
            f"{a.initial_value:.2f}",
            f"{a.current_value:.2f}",
            a.category or "",
            a.subcategory or "",
            ", ".join(a.tags) if a.tags else "",
        ])
    rows.append([
        "",
        "TOTAL",
        "",
        "",
        "",
        f"{status.total_initial:.2f}",
        f"{status.total_current:.2f}",
        "",
        "",
        "",
    ])
    click.echo(tabulate(
        rows, headers=asset_headers, tablefmt="simple",
        colalign=asset_colalign, disable_numparse=True,
    ))
    click.echo()

    # --- Table 2: Classes ---
    click.echo(separator)
    click.echo("Classes")
    click.echo(separator)
    class_headers = ["name", "total", "pct", "target", "target pct", "diff"]
    class_colalign = ("left", "right", "right", "right", "right", "right")
    class_rows = []
    for c in status.classes:
        class_rows.append([
            c.name,
            f"{c.total:.2f}",
            f"{c.pct:.2f}%",
            f"{c.target:.2f}",
            f"{c.target_pct:.2f}%",
            f"{c.diff:.2f}",
        ])
    click.echo(tabulate(
        class_rows, headers=class_headers, tablefmt="simple",
        colalign=class_colalign, disable_numparse=True,
    ))
    click.echo()

    # --- Table 3: Tags ---
    click.echo(separator)
    click.echo("Tags")
    click.echo(separator)
    tag_headers = ["name", "total", "pct", "target", "target pct", "diff"]
    tag_colalign = ("left", "right", "right", "right", "right", "right")
    tag_rows = []
    for t in status.tags:
        tag_rows.append([
            t.name,
            f"{t.total:.2f}",
            f"{t.pct:.2f}%",
            f"{t.target:.2f}",
            f"{t.target_pct:.2f}%",
            f"{t.diff:.2f}",
        ])
    if tag_rows:
        click.echo(tabulate(
            tag_rows, headers=tag_headers, tablefmt="simple",
            colalign=tag_colalign, disable_numparse=True,
        ))
    else:
        click.echo("no tags found.")
    click.echo(separator)
