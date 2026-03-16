import click
from tabulate import tabulate

from bed.commands.db import get_session, run_async
from bed.commands.utils import resolve_asset_id
from bed.models.asset import AssetClass, AssetType
from bed.schemas.asset import AssetCreate, AssetUpdate
from bed.services import assets as service
from bed.services import bonds as bonds_service
from bed.services import stocks as stocks_service


@click.group("asset")
def asset():
    """Manage portfolio assets."""
    pass


@asset.command("list")
@click.option("--update", "-u", is_flag=True, default=False, help="Update stock and bond prices before listing")
@click.option("--category", is_flag=True, default=False, help="Show category column")
@click.option("--subcat", is_flag=True, default=False, help="Show subcategory column")
def list_assets(update, category, subcat):
    """List all assets."""

    async def _run():
        async with get_session() as db:
            if update:
                click.echo("updating stock prices...")
                await stocks_service.update_prices(db)
                click.echo("updating bond prices...")
                await bonds_service.update_prices(db)
            return await service.list_assets(db)

    items = run_async(_run())
    if not items:
        click.echo("no assets found.")
        return

    table = []
    for i, a in enumerate(items, 1):
        if a.initial_value and a.initial_value != 0:
            pl_pct = ((a.current_value - a.initial_value) / a.initial_value) * 100
            pl_str = f"{pl_pct:+.2f}%"
        else:
            pl_str = ""
        row = [
            i,
            a.name,
            a.asset_class.value if a.asset_class else "",
            a.asset_type.value if a.asset_type else "",
            f"{a.quantity:.4f}",
            f"{a.initial_value:.2f}",
            f"{a.current_value:.2f}",
            pl_str,
        ]
        if category:
            row.append(a.category or "")
        if subcat:
            row.append(a.subcategory or "")
        row.append(", ".join(a.tags) if a.tags else "")
        table.append(row)

    headers = ["#", "name", "class", "type", "qty", "initial", "current", "p/l %"]
    colalign = ["right", "left", "left", "left", "right", "right", "right", "right"]
    if category:
        headers.append("category")
        colalign.append("left")
    if subcat:
        headers.append("subcat")
        colalign.append("left")
    headers.append("tags")
    colalign.append("left")
    click.echo(tabulate(table, headers=headers, tablefmt="simple", colalign=tuple(colalign)))


@asset.command("create")
@click.option("--name", "-n", required=True, help="Asset name")
@click.option("--description", "-d", default=None, help="Asset description")
@click.option(
    "--class", "asset_class", required=True,
    type=click.Choice([c.value for c in AssetClass], case_sensitive=False),
    help="Asset class",
)
@click.option(
    "--type", "asset_type", required=True,
    type=click.Choice([t.value for t in AssetType], case_sensitive=False),
    help="Asset type",
)
@click.option("--quantity", "-q", type=float, default=0, help="Quantity")
@click.option("--initial-value", "-i", type=float, default=0, help="Initial value")
@click.option("--current-value", "-c", type=float, default=0, help="Current value")
@click.option("--category", default=None, help="Category")
@click.option("--subcategory", default=None, help="Subcategory")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def create_asset(name, description, asset_class, asset_type, quantity, initial_value, current_value, category, subcategory, tags):
    """Create a new asset."""

    async def _run():
        async with get_session() as db:
            data = AssetCreate(
                name=name,
                description=description,
                asset_class=AssetClass(asset_class),
                asset_type=AssetType(asset_type),
                quantity=quantity,
                initial_value=initial_value,
                current_value=current_value,
                category=category,
                subcategory=subcategory,
                tags=[t.strip() for t in tags.split(",")] if tags else [],
            )
            result = await service.create_asset(db, data)
            click.echo(f"asset '{result.name}' created.")

    run_async(_run())


@asset.command("edit")
@click.argument("identifier")
@click.option("--name", "-n", default=None, help="Asset name")
@click.option("--description", "-d", default=None, help="Asset description")
@click.option(
    "--class", "asset_class", default=None,
    type=click.Choice([c.value for c in AssetClass], case_sensitive=False),
    help="Asset class",
)
@click.option(
    "--type", "asset_type", default=None,
    type=click.Choice([t.value for t in AssetType], case_sensitive=False),
    help="Asset type",
)
@click.option("--quantity", "-q", type=float, default=None, help="Quantity")
@click.option("--initial-value", "-i", type=float, default=None, help="Initial value")
@click.option("--current-value", "-c", type=float, default=None, help="Current value")
@click.option("--category", default=None, help="Category")
@click.option("--subcategory", default=None, help="Subcategory")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def edit_asset(identifier, name, description, asset_class, asset_type, quantity, initial_value, current_value, category, subcategory, tags):
    """Edit an existing asset."""

    async def _run():
        async with get_session() as db:
            asset_id = await resolve_asset_id(db, identifier)
            if not asset_id:
                click.echo(f"asset '{identifier}' not found.")
                return

            data = AssetUpdate(
                name=name,
                description=description,
                asset_class=AssetClass(asset_class) if asset_class else None,
                asset_type=AssetType(asset_type) if asset_type else None,
                quantity=quantity,
                initial_value=initial_value,
                current_value=current_value,
                category=category,
                subcategory=subcategory,
                tags=[t.strip() for t in tags.split(",")] if tags else None,
            )
            result = await service.update_asset(db, asset_id, data)
            if result:
                click.echo(f"asset '{result.name}' updated.")
            else:
                click.echo(f"asset '{identifier}' not found.")

    run_async(_run())


@asset.command("delete")
@click.argument("identifier")
@click.confirmation_option(prompt="Are you sure you want to delete this asset?")
def delete_asset(identifier):
    """Delete an asset."""

    async def _run():
        async with get_session() as db:
            asset_id = await resolve_asset_id(db, identifier)
            if not asset_id:
                click.echo(f"asset '{identifier}' not found.")
                return
            if await service.delete_asset(db, asset_id):
                click.echo("asset deleted.")
            else:
                click.echo(f"asset '{identifier}' not found.")

    run_async(_run())
