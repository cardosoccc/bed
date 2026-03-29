import click
from tabulate import tabulate

from bed.commands.db import get_session, run_async
from bed.services.conciliate import conciliate


@click.command("conciliate")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Show all positions including matches")
def conciliate_cmd(verbose):
    """Compare transaction positions against asset records."""

    async def _run():
        async with get_session() as db:
            report = await conciliate(db)

            table = []

            if verbose:
                for ticker in report.matches:
                    table.append([ticker, "", "", "ok"])

            for m in report.mismatches:
                table.append([m.ticker, f"{m.txn_qty:.0f}", f"{m.asset_qty:.0f}", "qty mismatch"])

            for m in report.missing_assets:
                table.append([m.ticker, f"{m.txn_qty:.0f}", "-", "missing asset"])

            for a in report.orphan_assets:
                table.append([a.name, "-", f"{float(a.quantity):.0f}", "no transactions"])

            if table:
                headers = ["ticker", "txn_qty", "asset_qty", "status"]
                colalign = ("left", "right", "right", "left")
                click.echo(tabulate(table, headers=headers, tablefmt="simple", colalign=colalign))
                click.echo()

            n_mis = len(report.mismatches)
            n_miss = len(report.missing_assets)
            n_orph = len(report.orphan_assets)
            n_ok = len(report.matches)

            parts = []
            if n_ok:
                parts.append(f"{n_ok} ok")
            parts.append(f"{n_mis} mismatches")
            parts.append(f"{n_miss} missing assets")
            parts.append(f"{n_orph} orphan assets")
            click.echo(f"summary: {', '.join(parts)}.")

    run_async(_run())
