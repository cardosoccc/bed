import click
from tabulate import tabulate

from bed.commands.db import get_session, run_async
from bed.services import stocks as service


@click.group("stocks")
def stocks():
    """Manage stock tickers of interest."""
    pass


@stocks.command("list")
@click.option("--update", "-u", is_flag=True, default=False, help="Update prices before listing")
def list_tickers(update):
    """List tickers of interest with current prices."""

    async def _run():
        async with get_session() as db:
            if update:
                click.echo("updating prices...")
                await service.update_prices(db)
            return await service.list_tickers(db)

    items = run_async(_run())
    if not items:
        click.echo("no tickers found.")
        return

    table = []
    for t in items:
        table.append([t.ticker, f"{t.price:.2f}"])
    headers = ["ticker", "price"]
    colalign = ("left", "right")
    click.echo(tabulate(table, headers=headers, tablefmt="simple", colalign=colalign))


@stocks.command("update")
def update_prices():
    """Update prices for all tickers of interest."""

    async def _run():
        async with get_session() as db:
            return await service.update_prices(db)

    click.echo("updating prices...")
    prices = run_async(_run())
    if not prices:
        click.echo("no tickers to update.")
        return

    for ticker, price in sorted(prices.items()):
        if price is not None:
            click.echo(f"  {ticker}: {price:.2f}")
        else:
            click.echo(f"  {ticker}: failed to fetch")
    click.echo("prices updated.")


@stocks.command("add")
@click.argument("ticker")
def add_ticker(ticker):
    """Add a ticker to the list of interest."""
    ticker = ticker.lower()

    async def _run():
        async with get_session() as db:
            existing = await service.get_ticker(db, ticker)
            if existing:
                click.echo(f"ticker '{ticker}' already in the list.")
                return

            # Validate ticker exists on B3 via yfinance
            prices = service.fetch_prices([ticker])
            if prices.get(ticker) is None:
                click.echo(f"ticker '{ticker}' not found. check if it exists on B3.")
                return

            obj = await service.add_ticker(db, ticker)
            obj.price = prices[ticker]
            await db.commit()
            click.echo(f"ticker '{ticker}' added (price: {prices[ticker]:.2f}).")

    run_async(_run())


@stocks.command("remove")
@click.argument("ticker")
def remove_ticker(ticker):
    """Remove a ticker from the list of interest."""
    ticker = ticker.lower()

    async def _run():
        async with get_session() as db:
            if await service.remove_ticker(db, ticker):
                click.echo(f"ticker '{ticker}' removed.")
            else:
                click.echo(f"ticker '{ticker}' not found in the list.")

    run_async(_run())
