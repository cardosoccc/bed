import click
from tabulate import tabulate

from bed.commands.db import get_session, run_async
from bed.commands.utils import resolve_goal_id
from bed.models.goal import GoalClass
from bed.schemas.goal import GoalCreate, GoalUpdate
from bed.services import goals as service


@click.group("goal")
def goal():
    """Manage investment goals."""
    pass


@goal.command("list")
def list_goals():
    """List all goals."""

    async def _run():
        async with get_session() as db:
            return await service.list_goals(db)

    items = run_async(_run())
    if not items:
        click.echo("No goals found.")
        return

    table = []
    for i, g in enumerate(items, 1):
        table.append([
            i,
            g.description,
            g.goal_class.value if g.goal_class else "",
            f"{g.quantity:.4f}" if g.quantity is not None else "",
            f"{g.value:.2f}" if g.value is not None else "",
        ])
    headers = ["#", "Description", "Class", "Quantity", "Value"]
    click.echo(tabulate(table, headers=headers, tablefmt="simple"))


@goal.command("create")
@click.option("--description", "-d", required=True, help="Goal description")
@click.option(
    "--class", "goal_class", required=True,
    type=click.Choice([c.value for c in GoalClass], case_sensitive=False),
    help="Goal class",
)
@click.option("--quantity", "-q", type=float, default=None, help="Target quantity")
@click.option("--value", "-v", type=float, default=None, help="Target value")
def create_goal(description, goal_class, quantity, value):
    """Create a new goal."""

    async def _run():
        async with get_session() as db:
            data = GoalCreate(
                description=description,
                goal_class=GoalClass(goal_class),
                quantity=quantity,
                value=value,
            )
            result = await service.create_goal(db, data)
            click.echo(f"Goal '{result.description}' created.")

    run_async(_run())


@goal.command("edit")
@click.argument("identifier")
@click.option("--description", "-d", default=None, help="Goal description")
@click.option(
    "--class", "goal_class", default=None,
    type=click.Choice([c.value for c in GoalClass], case_sensitive=False),
    help="Goal class",
)
@click.option("--quantity", "-q", type=float, default=None, help="Target quantity")
@click.option("--value", "-v", type=float, default=None, help="Target value")
def edit_goal(identifier, description, goal_class, quantity, value):
    """Edit an existing goal."""

    async def _run():
        async with get_session() as db:
            gid = await resolve_goal_id(db, identifier)
            if not gid:
                click.echo(f"Goal '{identifier}' not found.")
                return

            data = GoalUpdate(
                description=description,
                goal_class=GoalClass(goal_class) if goal_class else None,
                quantity=quantity,
                value=value,
            )
            result = await service.update_goal(db, gid, data)
            if result:
                click.echo(f"Goal '{result.description}' updated.")
            else:
                click.echo(f"Goal '{identifier}' not found.")

    run_async(_run())


@goal.command("delete")
@click.argument("identifier")
@click.confirmation_option(prompt="Are you sure you want to delete this goal?")
def delete_goal(identifier):
    """Delete a goal."""

    async def _run():
        async with get_session() as db:
            gid = await resolve_goal_id(db, identifier)
            if not gid:
                click.echo(f"Goal '{identifier}' not found.")
                return
            if await service.delete_goal(db, gid):
                click.echo("Goal deleted.")
            else:
                click.echo(f"Goal '{identifier}' not found.")

    run_async(_run())
