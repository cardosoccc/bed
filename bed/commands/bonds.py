import click
from tabulate import tabulate

from bed.commands.db import get_session, run_async
from bed.services import bonds as service


@click.group("bonds")
def bonds():
    """Manage Tesouro Direto bonds of interest."""
    pass


@bonds.command("list")
@click.option("--update", "-u", is_flag=True, default=False, help="Update prices before listing")
def list_bonds(update):
    """List bonds of interest with current prices."""

    async def _run():
        async with get_session() as db:
            if update:
                click.echo("updating prices...")
                await service.update_prices(db)
            return await service.list_bonds(db)

    items = run_async(_run())
    if not items:
        click.echo("no bonds found.")
        return

    table = []
    for b in items:
        table.append([b.name, f"{b.price:.2f}"])
    headers = ["name", "price"]
    colalign = ("left", "right")
    click.echo(tabulate(table, headers=headers, tablefmt="simple", colalign=colalign))


@bonds.command("update")
def update_prices():
    """Update prices for all bonds of interest (marcação a mercado)."""

    async def _run():
        async with get_session() as db:
            return await service.update_prices(db)

    click.echo("updating prices...")
    prices = run_async(_run())
    if not prices:
        click.echo("no bonds to update.")
        return

    for name, price in sorted(prices.items()):
        if price is not None:
            click.echo(f"  {name}: {price:.2f}")
        else:
            click.echo(f"  {name}: failed to fetch")
    click.echo("prices updated.")


@bonds.command("add")
@click.argument("name", nargs=-1, required=True)
def add_bond(name):
    """Add a bond to the list of interest.

    Use the full bond name (e.g. 'tesouro selic 2027') or a partial name to search.
    """
    query = " ".join(name).lower()

    async def _run():
        async with get_session() as db:
            # Fetch available bonds from the API
            api_prices = service.fetch_prices()
            if not api_prices:
                click.echo("failed to fetch bonds from Tesouro Direto API.")
                return

            # Try exact match first
            if query in api_prices:
                existing = await service.get_bond(db, query)
                if existing:
                    click.echo(f"bond '{query}' already in the list.")
                    return
                obj = await service.add_bond(db, query)
                obj.price = api_prices[query]
                await db.commit()
                click.echo(f"bond '{query}' added (price: {api_prices[query]:.2f}).")
                return

            # Search by partial match
            matches = service.search_bonds(query, api_prices)
            if not matches:
                click.echo(f"no bonds matching '{query}' found.")
                click.echo("available bonds:")
                for bond_name in sorted(api_prices.keys()):
                    click.echo(f"  {bond_name}")
                return

            if len(matches) == 1:
                bond_name, price = matches[0]
                existing = await service.get_bond(db, bond_name)
                if existing:
                    click.echo(f"bond '{bond_name}' already in the list.")
                    return
                obj = await service.add_bond(db, bond_name)
                obj.price = price
                await db.commit()
                click.echo(f"bond '{bond_name}' added (price: {price:.2f}).")
                return

            click.echo(f"multiple bonds match '{query}':")
            for bond_name, price in matches:
                p = f"{price:.2f}" if price else "n/a"
                click.echo(f"  {bond_name} ({p})")
            click.echo("please use a more specific name.")

    run_async(_run())


@bonds.command("remove")
@click.argument("name", nargs=-1, required=True)
def remove_bond(name):
    """Remove a bond from the list of interest."""
    bond_name = " ".join(name).lower()

    async def _run():
        async with get_session() as db:
            if await service.remove_bond(db, bond_name):
                click.echo(f"bond '{bond_name}' removed.")
            else:
                click.echo(f"bond '{bond_name}' not found in the list.")

    run_async(_run())


@bonds.command("search")
@click.argument("query", nargs=-1, required=True)
def search_bonds(query):
    """Search available Tesouro Direto bonds by name."""
    q = " ".join(query).lower()

    api_prices = service.fetch_prices()
    if not api_prices:
        click.echo("failed to fetch bonds from Tesouro Direto API.")
        return

    matches = service.search_bonds(q, api_prices)
    if not matches:
        click.echo(f"no bonds matching '{q}' found.")
        return

    table = []
    for name, price in matches:
        p = f"{price:.2f}" if price else "n/a"
        table.append([name, p])
    headers = ["name", "price"]
    colalign = ("left", "right")
    click.echo(tabulate(table, headers=headers, tablefmt="simple", colalign=colalign))
