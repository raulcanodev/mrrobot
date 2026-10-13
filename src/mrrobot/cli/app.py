"""CLI entry point (Typer).

The CLI is a thin layer over the core: it translates commands into
registry/runner calls and renders results with Rich. All reusable logic
lives in mrrobot.core (and in actions.py for what's shared with the menu),
so a future interface (a Textual TUI) could lean on exactly the same code.

With no arguments, 'mrrobot' opens the interactive menu (an arrow-key
selector). Every menu action also has its own direct command — the menu is
never the only way to do something.
"""

from __future__ import annotations

import typer

from .. import __version__
from ..core import registry
from ..core.config import SCOPE_FILE, load_scope, write_scope_template
from ..core.console import console, err_console
from . import actions
from .banner import render_banner
from .report_wizard import run_wizard

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="mrrobot — modular orchestrator for authorized OSINT & pentesting.",
    rich_markup_mode="rich",
)

scope_app = typer.Typer(help="Manage your authorized scope.")
tools_app = typer.Typer(help="List, check and install tools.")
app.add_typer(scope_app, name="scope")
app.add_typer(tools_app, name="tools")


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show the version and exit."),
) -> None:
    if version:
        console.print(f"mrrobot v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        # No arguments: interactive menu. Any subcommand still goes through
        # the usual manual path (its behavior is unchanged).
        from .menu import main_menu

        main_menu()


@app.command("menu")
def menu_command() -> None:
    """Open the interactive menu (same as running 'mrrobot' with nothing else)."""
    from .menu import main_menu

    main_menu()


@tools_app.callback(invoke_without_command=True)
def tools_list(
    ctx: typer.Context,
    online: bool = typer.Option(
        False, "--online/--offline",
        help="Check GitHub for newer versions.",
    ),
) -> None:
    """List the built-in tools and their status."""
    if ctx.invoked_subcommand is not None:
        return
    actions.print_tools_table(online)


@tools_app.command("install")
def tools_install(
    name: str = typer.Argument(None, help="Tool name. Omit if using --all."),
    all_missing: bool = typer.Option(
        False, "--all", help="Install every missing external tool in one go."
    ),
) -> None:
    """Install an external tool, or every missing one with --all."""
    if all_missing:
        actions.install_all_missing()
        return
    if not name:
        err_console.print("[err]Give a name, or use '--all' to install everything.[/err]")
        raise typer.Exit(code=2)
    ok = actions.install_one(name)
    raise typer.Exit(code=0 if ok else 1)


@scope_app.command("init")
def scope_init() -> None:
    """Create the authorized-scope template and show its path."""
    path = write_scope_template()
    console.print(f"[ok]✓[/ok] Scope template at: [bold]{path}[/bold]")
    console.print("[muted]Edit it with your authorized targets and set authorized = true.[/muted]")


@scope_app.command("show")
def scope_show() -> None:
    """Show the current authorized scope."""
    scope = load_scope()
    if not SCOPE_FILE.exists():
        console.print("[warn]No scope defined.[/warn] Run 'mrrobot scope init'.")
        raise typer.Exit()
    status = "[ok]authorized[/ok]" if scope.authorized else "[err]NOT authorized[/err]"
    console.print(f"Status:   {status}")
    console.print(f"Domains:  {scope.domains or '—'}")
    console.print(f"Networks: {scope.networks or '—'}")


@app.command()
def run(
    tool: str = typer.Argument(..., help="Tool name (see 'mrrobot tools')."),
    target: str = typer.Argument(..., help="Target: username, domain or IP depending on the tool."),
    timeout: int = typer.Option(300, help="Maximum run time in seconds."),
    ports: str = typer.Option("", help="Ports for network tools, e.g. '1-1000'."),
) -> None:
    """Run a tool against a target."""
    adapter = registry.get(tool)
    if adapter is None:
        err_console.print(f"[err]Unknown tool:[/err] {tool}")
        err_console.print("[muted]Run 'mrrobot tools' to see what's available.[/muted]")
        raise typer.Exit(code=2)

    scope = load_scope()
    actions.execute_tool(adapter, target, scope=scope, timeout=timeout, ports=ports or None)


@app.command()
def history(limit: int = typer.Option(20, help="Number of runs to show.")) -> None:
    """Show the saved run history."""
    actions.print_history(limit)


@app.command()
def report(
    target: str = typer.Argument(None, help="Domain, username or IP. Asked for if omitted."),
) -> None:
    """Interactive wizard: pick tools and generate a full report."""
    render_banner(__version__)
    run_wizard(target)


@app.command()
def doctor(
    online: bool = typer.Option(
        True, "--online/--offline", help="Check for updates over the network."
    ),
) -> None:
    """Startup check: which tools are present, and any available updates."""
    render_banner(__version__)
    actions.print_startup_notices(online)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
