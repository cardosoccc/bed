import click
from tabulate import tabulate

from bed.commands.db import get_session, run_async
from bed.commands.utils import resolve_rule_id
from bed.schemas.rule import RuleCreate, RuleUpdate
from bed.services import rules as service


@click.group("rule")
def rule():
    """Manage portfolio rules."""
    pass


@rule.command("list")
def list_rules():
    """List all rules."""

    async def _run():
        async with get_session() as db:
            return await service.list_rules(db)

    items = run_async(_run())
    if not items:
        click.echo("no rules found.")
        return

    table = []
    for i, r in enumerate(items, 1):
        table.append([
            i,
            r.description,
            f"{r.invested_value:.2f}" if r.invested_value is not None else "",
            f"{r.current_value:.2f}" if r.current_value is not None else "",
            r.asset_class or "",
            r.asset_type or "",
            r.category or "",
            r.subcategory or "",
            ", ".join(r.tags) if r.tags else "",
        ])
    headers = ["#", "description", "invested", "current", "class", "type", "category", "subcat", "tags"]
    colalign = ("right", "left", "right", "right", "left", "left", "left", "left", "left")
    click.echo(tabulate(table, headers=headers, tablefmt="simple", colalign=colalign))


@rule.command("create")
@click.option("--description", "-d", required=True, help="Rule description")
@click.option("--invested-value", "-i", type=float, default=None, help="Invested value limit")
@click.option("--current-value", "-c", type=float, default=None, help="Current value limit")
@click.option("--class", "asset_class", default=None, help="Asset class filter")
@click.option("--type", "asset_type", default=None, help="Asset type filter")
@click.option("--category", default=None, help="Category filter")
@click.option("--subcategory", default=None, help="Subcategory filter")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def create_rule(description, invested_value, current_value, asset_class, asset_type, category, subcategory, tags):
    """Create a new rule."""

    async def _run():
        async with get_session() as db:
            data = RuleCreate(
                description=description,
                invested_value=invested_value,
                current_value=current_value,
                asset_class=asset_class,
                asset_type=asset_type,
                category=category,
                subcategory=subcategory,
                tags=[t.strip() for t in tags.split(",")] if tags else [],
            )
            result = await service.create_rule(db, data)
            click.echo(f"rule '{result.description}' created.")

    run_async(_run())


@rule.command("edit")
@click.argument("identifier")
@click.option("--description", "-d", default=None, help="Rule description")
@click.option("--invested-value", "-i", type=float, default=None, help="Invested value limit")
@click.option("--current-value", "-c", type=float, default=None, help="Current value limit")
@click.option("--class", "asset_class", default=None, help="Asset class filter")
@click.option("--type", "asset_type", default=None, help="Asset type filter")
@click.option("--category", default=None, help="Category filter")
@click.option("--subcategory", default=None, help="Subcategory filter")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def edit_rule(identifier, description, invested_value, current_value, asset_class, asset_type, category, subcategory, tags):
    """Edit an existing rule."""

    async def _run():
        async with get_session() as db:
            rid = await resolve_rule_id(db, identifier)
            if not rid:
                click.echo(f"rule '{identifier}' not found.")
                return

            data = RuleUpdate(
                description=description,
                invested_value=invested_value,
                current_value=current_value,
                asset_class=asset_class,
                asset_type=asset_type,
                category=category,
                subcategory=subcategory,
                tags=[t.strip() for t in tags.split(",")] if tags else None,
            )
            result = await service.update_rule(db, rid, data)
            if result:
                click.echo(f"rule '{result.description}' updated.")
            else:
                click.echo(f"rule '{identifier}' not found.")

    run_async(_run())


@rule.command("delete")
@click.argument("identifier")
@click.confirmation_option(prompt="Are you sure you want to delete this rule?")
def delete_rule(identifier):
    """Delete a rule."""

    async def _run():
        async with get_session() as db:
            rid = await resolve_rule_id(db, identifier)
            if not rid:
                click.echo(f"rule '{identifier}' not found.")
                return
            if await service.delete_rule(db, rid):
                click.echo("rule deleted.")
            else:
                click.echo(f"rule '{identifier}' not found.")

    run_async(_run())
