"""Interactive menu: arrow-key navigation, without losing the manual path.

Opens when running 'mrrobot' with no arguments (or 'mrrobot menu'). Every
option here also has its own direct command documented in 'mrrobot
--help' — the menu is just a more convenient way to reach the same thing.
"""

from __future__ import annotations

import sys

import questionary

from .. import __version__
from ..core import registry
from ..core.config import SCOPE_FILE, load_scope, write_scope_template
from ..core.console import console
from ..core.models import TargetKind
from . import actions
from .banner import render_banner
from .report_wizard import run_wizard
from .style import QUESTIONARY_STYLE as _STYLE

_BACK = "‹ Back"

_TARGET_HINTS = {
    TargetKind.USERNAME: "username",
    TargetKind.DOMAIN: "domain",
    TargetKind.IP: "IP address",
    TargetKind.HOST: "domain or IP",
}

_MAIN_CHOICES = [
    "Run a tool",
    "Generate a full report",
    "View tool status",
    "Install missing tools",
    "Manage scope",
    "View history",
    "Exit",
]


def main_menu() -> None:
    if not sys.stdin.isatty():
        console.print(
            "[muted]No interactive terminal available; "
            "use direct commands instead ('mrrobot --help').[/muted]"
        )
        return

    render_banner(__version__)
    console.print(
        "[muted]↑/↓ to move, Enter to choose. "
        "You can also use direct commands: 'mrrobot --help'.[/muted]\n"
    )
    _maybe_offer_self_update()

    try:
        while True:
            choice = questionary.select(
                "What do you want to do?", choices=_MAIN_CHOICES, style=_STYLE
            ).ask()
            if choice is None or choice == "Exit":
                console.print("[muted]Bye.[/muted]")
                return

            console.print()
            if choice == "Run a tool":
                _run_tool_flow()
            elif choice == "Generate a full report":
                run_wizard(None)
            elif choice == "View tool status":
                actions.print_tools_table(online=False)
            elif choice == "Install missing tools":
                actions.install_all_missing()
            elif choice == "Manage scope":
                _scope_flow()
            elif choice == "View history":
                actions.print_history(20)
            console.print()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[muted]Bye.[/muted]")


def _run_tool_flow() -> None:
    adapters = sorted(registry.all_adapters(), key=lambda a: (a.meta.category.value, a.meta.name))
    labels = [
        f"{a.meta.name}  ({a.meta.category.value}/{a.meta.mode.value}) — {a.meta.summary}"
        for a in adapters
    ]
    choice = questionary.select(
        "Which tool do you want to run?",
        choices=[*labels, _BACK],
        style=_STYLE,
    ).ask()
    if choice is None or choice == _BACK:
        return

    adapter = adapters[labels.index(choice)]
    hint = _TARGET_HINTS[adapter.meta.target_kind]
    target = questionary.text(f"Target ({hint}):", style=_STYLE).ask()
    if not target or not target.strip():
        return
    target = target.strip()

    extra: dict[str, object] = {}
    if adapter.meta.name == "nmap":
        ports = questionary.text(
            "Ports (optional, e.g. '1-1000'; Enter for the default scan):",
            style=_STYLE,
        ).ask()
        extra["ports"] = ports.strip() if ports else None

    scope = load_scope()
    actions.execute_tool(adapter, target, scope=scope, **extra)


def _scope_flow() -> None:
    choice = questionary.select(
        "Authorized scope",
        choices=["View current status", "Create/open template", _BACK],
        style=_STYLE,
    ).ask()
    if choice is None or choice == _BACK:
        return
    if choice == "View current status":
        if not SCOPE_FILE.exists():
            console.print("[warn]No scope defined yet.[/warn]")
            return
        scope = load_scope()
        status = "[ok]authorized[/ok]" if scope.authorized else "[err]NOT authorized[/err]"
        console.print(f"Status:   {status}")
        console.print(f"Domains:  {scope.domains or '—'}")
        console.print(f"Networks: {scope.networks or '—'}")
    elif choice == "Create/open template":
        path = write_scope_template()
        console.print(f"[ok]✓[/ok] Template at: [bold]{path}[/bold]")
        console.print("[muted]Edit it by hand and set authorized = true.[/muted]")


def _maybe_offer_self_update() -> None:
    """Best-effort, quiet-on-failure check for a newer mrrobot on startup."""
    try:
        available, current, latest = actions.get_self_update_status(timeout=2.5)
    except Exception:
        # Never let a flaky network keep the menu from opening.
        return
    if not available or not current or not latest:
        return

    console.print(
        f"[warn]↑ A new version of mrrobot is available[/warn] "
        f"({current[:7]} → {latest[:7]}).\n"
    )
    if questionary.confirm("Update now?", default=True, style=_STYLE).ask():
        actions.self_update()
        raise SystemExit(0)
    console.print()
