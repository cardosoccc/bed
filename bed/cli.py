import copy

import click

from bed.commands.assets import asset
from bed.commands.rules import rule
from bed.commands.stocks import stocks
from bed.commands.db_commands import portfolio
from bed.commands.credentials import configure_aws, configure_gcp
from bed.commands.config_store import set_config_value, load_config


def _list_alias(list_cmd: click.Command, alias_for: str, resource: str) -> click.Command:
    @click.pass_context
    def _callback(ctx, **kwargs):
        return ctx.invoke(list_cmd, **kwargs)

    return click.Command(
        name=None,
        callback=_callback,
        params=list(list_cmd.params),
        help=f"List {resource}  (alias for: {alias_for})",
    )


def _add_subcommand_aliases(group: click.Group, aliases: dict[str, str]) -> None:
    for alias, name in aliases.items():
        if name in group.commands:
            _add_visible_alias(group, group.commands[name], alias, name)


def _add_visible_alias(group: click.Group, cmd: click.Command, alias: str, canonical_name: str) -> None:
    cmd.hidden = True

    visible = copy.copy(cmd)
    visible.hidden = False
    raw = cmd.short_help or (cmd.help or "").split("\n")[0]
    base_short = raw.split("(alias for:")[0].rstrip(". ")
    visible.short_help = f"{base_short}  (alias for: {canonical_name})"
    group.add_command(visible, name=alias)


@click.group()
def cli():
    """bed - Portfolio management CLI."""
    pass


cli.add_command(portfolio)
cli.add_command(asset)
cli.add_command(rule)
cli.add_command(stocks)


@cli.group("config")
def config():
    """Manage CLI configuration."""
    pass


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    set_config_value(key, value)
    click.echo(f"{key}: {value}")


@config.command("list")
def config_list():
    """List current configurations."""
    cfg = load_config()
    if not cfg:
        click.echo("no configuration values set.")
        return
    for k, v in cfg.items():
        click.echo(f"{k}: {v}")


config.add_command(configure_aws)
config.add_command(configure_gcp)


# Subcommand aliases (e=edit, c=create, d=delete, l=list)
_crud_aliases = {"e": "edit", "c": "create", "d": "delete", "l": "list"}
for _grp in (asset, rule):
    _add_subcommand_aliases(_grp, _crud_aliases)

_add_subcommand_aliases(config, {"s": "set"})
_add_subcommand_aliases(portfolio, {"s": "status"})
_add_subcommand_aliases(stocks, {"l": "list", "u": "update", "a": "add", "r": "remove"})

# Command group aliases — single letter
_add_visible_alias(cli, asset, "a", "asset")
_add_visible_alias(cli, rule, "r", "rule")
_add_visible_alias(cli, stocks, "s", "stocks")
_add_visible_alias(cli, portfolio, "p", "portfolio")
_add_visible_alias(cli, cli.commands["config"], "c", "config")

# Double-letter list shortcuts
cli.add_command(_list_alias(asset.commands["list"], "a list", "assets"), name="aa")
cli.add_command(_list_alias(rule.commands["list"], "r list", "rules"), name="rr")
cli.add_command(_list_alias(stocks.commands["list"], "s list", "stocks"), name="ss")
cli.add_command(_list_alias(portfolio.commands["status"], "p status", "portfolio status"), name="pp")


if __name__ == "__main__":
    cli()
