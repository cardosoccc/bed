from datetime import datetime

import click
from tabulate import tabulate

from bed.commands.db import get_session, run_async
from bed.commands.utils import resolve_transaction_id
from bed.schemas.transaction import TransactionCreate, TransactionUpdate
from bed.services import transactions as service
from bed.services.transactions import compute_row_hash
from bed.services.xlsx_import import apply_sign, parse_xlsx


@click.group("transaction", invoke_without_command=True)
@click.pass_context
def transaction(ctx):
    """Manage transactions."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_transactions)


@transaction.command("list")
@click.option("--ticker", "-k", default=None, help="Filter by ticker")
@click.option("--type", "-m", "type_filter", default=None, help="Filter by movimentação type")
@click.option("--institution", "-i", default=None, help="Filter by institution")
@click.option("--from", "-f", "date_from", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--to", "-o", "date_to", default=None, help="End date (YYYY-MM-DD)")
@click.option("--limit", "-n", type=int, default=50, help="Max rows (default: 50)")
@click.option("--all", "show_all", is_flag=True, default=False, help="Show all (no limit)")
def list_transactions(ticker, type_filter, institution, date_from, date_to, limit, show_all):
    """List transactions."""

    async def _run():
        async with get_session() as db:
            df = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
            dt = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
            return await service.list_transactions(
                db,
                ticker=ticker,
                type_filter=type_filter,
                institution=institution,
                date_from=df,
                date_to=dt,
                limit=None if show_all else limit,
            )

    items = run_async(_run())
    if not items:
        click.echo("no transactions found.")
        return

    table = []
    for i, t in enumerate(items, 1):
        table.append([
            i,
            str(t.date),
            t.type,
            t.ticker or "",
            t.product[:40],
            t.institution,
            f"{t.quantity:.4f}",
            f"{t.unit_value:.2f}",
            f"{t.total_value:.2f}",
            ", ".join(t.tags) if t.tags else "",
        ])

    headers = ["#", "date", "type", "ticker", "product", "inst", "qty", "unit", "total", "tags"]
    colalign = ("right", "left", "left", "left", "left", "left", "right", "right", "right", "left")
    click.echo(tabulate(table, headers=headers, tablefmt="simple", colalign=colalign))


@transaction.command("create")
@click.option("--date", "-d", "txn_date", required=True, help="Transaction date (YYYY-MM-DD)")
@click.option("--type", "-m", "txn_type", required=True, help="Transaction type")
@click.option("--product", "-p", required=True, help="Product name")
@click.option("--ticker", "-k", default=None, help="Ticker symbol")
@click.option("--institution", "-i", required=True, help="Institution (short name)")
@click.option("--quantity", "-q", type=float, default=0, help="Quantity")
@click.option("--unit-value", "-u", type=float, default=0, help="Unit value")
@click.option("--total-value", "-v", type=float, default=0, help="Total value (negative for debit)")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def create_transaction(txn_date, txn_type, product, ticker, institution, quantity, unit_value, total_value, tags):
    """Create a new transaction."""

    async def _run():
        async with get_session() as db:
            data = TransactionCreate(
                date=datetime.strptime(txn_date, "%Y-%m-%d").date(),
                type=txn_type,
                product=product,
                ticker=ticker,
                institution=institution,
                quantity=quantity,
                unit_value=unit_value,
                total_value=total_value,
                tags=[t.strip() for t in tags.split(",")] if tags else [],
            )
            result = await service.create_transaction(db, data)
            click.echo(f"transaction created ({result.date} {result.type} {result.product}).")

    run_async(_run())


@transaction.command("edit")
@click.argument("identifier")
@click.option("--date", "-d", "txn_date", default=None, help="Transaction date (YYYY-MM-DD)")
@click.option("--type", "-m", "txn_type", default=None, help="Transaction type")
@click.option("--product", "-p", default=None, help="Product name")
@click.option("--ticker", "-k", default=None, help="Ticker symbol")
@click.option("--institution", "-i", default=None, help="Institution")
@click.option("--quantity", "-q", type=float, default=None, help="Quantity")
@click.option("--unit-value", "-u", type=float, default=None, help="Unit value")
@click.option("--total-value", "-v", type=float, default=None, help="Total value")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def edit_transaction(identifier, txn_date, txn_type, product, ticker, institution, quantity, unit_value, total_value, tags):
    """Edit an existing transaction."""

    async def _run():
        async with get_session() as db:
            txn_id = await resolve_transaction_id(db, identifier)
            if not txn_id:
                click.echo(f"transaction '{identifier}' not found.")
                return

            data = TransactionUpdate(
                date=datetime.strptime(txn_date, "%Y-%m-%d").date() if txn_date else None,
                type=txn_type,
                product=product,
                ticker=ticker,
                institution=institution,
                quantity=quantity,
                unit_value=unit_value,
                total_value=total_value,
                tags=[t.strip() for t in tags.split(",")] if tags else None,
            )
            result = await service.update_transaction(db, txn_id, data)
            if result:
                click.echo("transaction updated.")
            else:
                click.echo(f"transaction '{identifier}' not found.")

    run_async(_run())


@transaction.command("delete")
@click.argument("identifier")
@click.confirmation_option(prompt="Are you sure you want to delete this transaction?")
def delete_transaction(identifier):
    """Delete a transaction."""

    async def _run():
        async with get_session() as db:
            txn_id = await resolve_transaction_id(db, identifier)
            if not txn_id:
                click.echo(f"transaction '{identifier}' not found.")
                return
            if await service.delete_transaction(db, txn_id):
                click.echo("transaction deleted.")
            else:
                click.echo(f"transaction '{identifier}' not found.")

    run_async(_run())


@transaction.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("--sheet", default="Movimentação", help="Sheet name")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without importing")
def import_transactions(file, sheet, dry_run):
    """Import transactions from B3 XLSX export."""

    async def _run():
        async with get_session() as db:
            click.echo(f"parsing {file}...")
            raw_rows = parse_xlsx(file, sheet_name=sheet)
            click.echo(f"found {len(raw_rows)} rows.")

            # Load asset tags for inference
            from bed.services.assets import list_assets

            assets = await list_assets(db)
            ticker_tags = {}
            for asset in assets:
                if " - " in asset.name:
                    asset_ticker = asset.name.split(" - ")[0].strip()
                else:
                    asset_ticker = asset.name
                if asset.tags:
                    ticker_tags[asset_ticker] = list(asset.tags)

            # Build TransactionCreate objects
            items = []
            for row in raw_rows:
                total = apply_sign(row["total_value"], row["entrada_saida"])
                row_tags = ticker_tags.get(row["ticker"], [])
                row_hash = compute_row_hash(
                    row["date"], row["type"], row["product"],
                    row["institution"], row["quantity"], row["unit_value"], total,
                )
                items.append(TransactionCreate(
                    date=row["date"],
                    type=row["type"],
                    product=row["product"],
                    ticker=row["ticker"],
                    institution=row["institution"],
                    quantity=row["quantity"],
                    unit_value=row["unit_value"],
                    total_value=total,
                    row_hash=row_hash,
                    tags=row_tags,
                ))

            if dry_run:
                click.echo(f"[dry-run] would import {len(items)} transactions.")
                for item in items[:10]:
                    click.echo(f"  {item.date} {item.type:30s} {item.ticker or '':10s} {item.total_value:>12.2f}")
                if len(items) > 10:
                    click.echo(f"  ... and {len(items) - 10} more")
                return

            imported, skipped = await service.bulk_create_transactions(db, items)
            click.echo(f"{imported} imported, {skipped} skipped (duplicates).")

    run_async(_run())
