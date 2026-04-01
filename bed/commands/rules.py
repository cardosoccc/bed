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
            "current" if r.current else "invested",
            f"{float(r.target):.2f}" if r.target is not None else "",
            f"{float(r.min):.2f}" if r.min is not None else "",
            f"{float(r.max):.2f}" if r.max is not None else "",
            r.asset_class or "",
            r.asset_type or "",
            r.category or "",
            r.subcategory or "",
            ", ".join(r.tags) if r.tags else "",
        ])
    headers = ["#", "description", "metric", "target", "min", "max", "class", "type", "category", "subcat", "tags"]
    colalign = ("right", "left", "left", "right", "right", "right", "left", "left", "left", "left", "left")
    click.echo(tabulate(
        table, headers=headers, tablefmt="simple",
        colalign=colalign, disable_numparse=True,
    ))


@rule.command("create")
@click.option("--description", "-d", required=True, help="Rule description")
@click.option("--target", type=float, default=None, help="Target value; 0..1 is treated as a percentage")
@click.option("--min", "min_value", type=float, default=None, help="Minimum value; 0..1 is treated as a percentage")
@click.option("--max", "max_value", type=float, default=None, help="Maximum value; 0..1 is treated as a percentage")
@click.option("--current/--invested", "current", default=True, help="Whether the rule applies to current or invested value")
@click.option("--class", "asset_class", default=None, help="Asset class filter")
@click.option("--type", "asset_type", default=None, help="Asset type filter")
@click.option("--category", default=None, help="Category filter")
@click.option("--subcategory", default=None, help="Subcategory filter")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def create_rule(description, target, min_value, max_value, current, asset_class, asset_type, category, subcategory, tags):
    """Create a new rule."""

    async def _run():
        async with get_session() as db:
            data = RuleCreate(
                description=description,
                current=current,
                target=target,
                min=min_value,
                max=max_value,
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
@click.option("--target", type=float, default=None, help="Target value; 0..1 is treated as a percentage")
@click.option("--min", "min_value", type=float, default=None, help="Minimum value; 0..1 is treated as a percentage")
@click.option("--max", "max_value", type=float, default=None, help="Maximum value; 0..1 is treated as a percentage")
@click.option("--clear-target", is_flag=True, help="Clear the target value")
@click.option("--clear-min", is_flag=True, help="Clear the minimum value")
@click.option("--clear-max", is_flag=True, help="Clear the maximum value")
@click.option("--current/--invested", "current", default=None, help="Whether the rule applies to current or invested value")
@click.option("--class", "asset_class", default=None, help="Asset class filter")
@click.option("--type", "asset_type", default=None, help="Asset type filter")
@click.option("--category", default=None, help="Category filter")
@click.option("--subcategory", default=None, help="Subcategory filter")
@click.option("--tags", "-t", default=None, help="Comma-separated tags")
def edit_rule(
    identifier, description, target, min_value, max_value,
    clear_target, clear_min, clear_max, current, asset_class, asset_type,
    category, subcategory, tags,
):
    """Edit an existing rule."""

    async def _run():
        async with get_session() as db:
            rid = await resolve_rule_id(db, identifier)
            if not rid:
                click.echo(f"rule '{identifier}' not found.")
                return

            payload = {}
            if description is not None:
                payload["description"] = description
            if current is not None:
                payload["current"] = current
            if clear_target:
                payload["target"] = None
            elif target is not None:
                payload["target"] = target
            if clear_min:
                payload["min"] = None
            elif min_value is not None:
                payload["min"] = min_value
            if clear_max:
                payload["max"] = None
            elif max_value is not None:
                payload["max"] = max_value
            if asset_class is not None:
                payload["asset_class"] = asset_class
            if asset_type is not None:
                payload["asset_type"] = asset_type
            if category is not None:
                payload["category"] = category
            if subcategory is not None:
                payload["subcategory"] = subcategory
            if tags is not None:
                payload["tags"] = [t.strip() for t in tags.split(",")]

            data = RuleUpdate(**payload)
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
