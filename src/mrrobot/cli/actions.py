"""Actions shared between direct commands and the interactive menu.

Both `mrrobot run ...` and the menu's selector call exactly the same
functions here, so there's never two implementations of the same thing,
or one path doing something the other doesn't.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import TypeVar

import httpx
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..core import registry, storage
from ..core.config import SELF_BRANCH, SELF_REPO, Scope
from ..core.console import console, err_console
from ..core.installer import pick_install_cmd
from ..core.models import Mode, ToolStatus
from ..core.runner import NotAuthorized, ToolNotInstalled, which
from ..core.updates import check_self_update, check_tool
from ..tools.base import ToolAdapter

T = TypeVar("T")


def run_with_progress(description: str, fn: Callable[[], T]) -> T:
    """Run a blocking call behind a live spinner + elapsed-time counter.

    Used for anything that can take a while (an external scan, a slow
    public API) so the user always sees what's running and for how long,
    instead of a silent or empty spinner.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description, total=None)
        return fn()


def check_all(online: bool) -> list[ToolStatus]:
    statuses: list[ToolStatus] = []
    client = httpx.Client(timeout=6.0) if online else None
    try:
        for adapter in registry.all_adapters():
            statuses.append(check_tool(adapter.meta, online=online, client=client))
    finally:
        if client is not None:
            client.close()
    return statuses


def print_startup_notices(online: bool) -> None:
    """On startup: warn about missing tools, tool updates, or an mrrobot update."""
    if online:
        self_available, self_current, self_latest = get_self_update_status()
        if self_available and self_current and self_latest:
            console.print(
                f"[warn]↑ A new version of mrrobot is available[/warn] "
                f"({self_current[:7]} → {self_latest[:7]}). Run 'mrrobot update'."
            )

    statuses = check_all(online)
    missing = [s for s in statuses if not s.installed]
    updates = [s for s in statuses if s.update_available]

    if missing:
        names = ", ".join(s.meta.name for s in missing)
        console.print(
            f"[warn]⚠ Not installed:[/warn] {names} "
            f"[muted](run 'mrrobot tools install --all' to install them)[/muted]"
        )
    if updates:
        for s in updates:
            console.print(
                f"[warn]↑ Update available:[/warn] {s.meta.name} "
                f"{s.installed_version} → [ok]{s.latest_version}[/ok]"
            )
    if not missing and not updates and online:
        console.print("[ok]✓ All built-in tools are up to date.[/ok]")


def print_tools_table(online: bool) -> list[ToolStatus]:
    """Print the tools table and return the ones that still need installing."""
    statuses = sorted(check_all(online), key=lambda s: (s.meta.category.value, s.meta.name))
    table = Table(title="Built-in tools", title_style="brand", expand=True)
    table.add_column("Tool", style="bold")
    table.add_column("Category")
    table.add_column("Mode")
    table.add_column("Installed")
    table.add_column("Version")
    if online:
        table.add_column("Latest")

    for s in statuses:
        mode_style = "active" if s.meta.mode is Mode.ACTIVE else "passive"
        version = "built-in" if s.meta.builtin else (s.installed_version or "—")
        row = [
            s.meta.name,
            s.meta.category.value,
            f"[{mode_style}]{s.meta.mode.value}[/{mode_style}]",
            "[ok]yes[/ok]" if s.installed else "[err]no[/err]",
            version,
        ]
        if online:
            latest = "—" if s.meta.builtin else (s.latest_version or "—")
            if s.update_available:
                latest = f"[warn]{latest} ↑[/warn]"
            row.append(latest)
        table.add_row(*row)

    console.print(table)
    missing = [s for s in statuses if not s.installed]
    if missing:
        console.print(
            "\n[muted]Install them with 'mrrobot tools install <name>' "
            "('--all' for all of them), or manually:[/muted]"
        )
        for s in missing:
            hint = s.meta.install_hint or "see the upstream repo"
            console.print(f"  • {s.meta.name}: [muted]{hint}[/muted]")
    return missing


def print_history(limit: int) -> None:
    rows = storage.recent_runs(limit)
    if not rows:
        console.print("[muted]No runs recorded yet.[/muted]")
        return
    table = Table(title="History", title_style="brand")
    table.add_column("#")
    table.add_column("Tool")
    table.add_column("Target")
    table.add_column("Mode")
    table.add_column("Exit")
    table.add_column("Dur. (s)")
    for r in rows:
        table.add_row(
            str(r["id"]), r["tool"], r["target"], r["mode"],
            str(r["returncode"]), str(r["duration_s"]),
        )
    console.print(table)
    console.print(f"[muted]Database: {storage.db_location()}[/muted]")


def execute_tool(
    adapter: ToolAdapter,
    target: str,
    *,
    scope: Scope,
    timeout: int = 300,
    **options: object,
) -> None:
    """Run a tool and show the result. Used by both 'run' and the menu."""
    mode = adapter.meta.mode
    label = "[active]ACTIVE[/active]" if mode is Mode.ACTIVE else "[passive]PASSIVE[/passive]"
    console.print(f"▶ {adapter.meta.name} ({label}) → [bold]{target}[/bold]")

    try:
        result = run_with_progress(
            f"Running {adapter.meta.name}…",
            lambda: adapter.run(target, scope=scope, timeout=timeout, **options),
        )
    except NotAuthorized as exc:
        err_console.print(f"[err]Blocked:[/err] {exc}")
        return
    except ToolNotInstalled as exc:
        err_console.print(f"[err]Not installed:[/err] {exc}")
        if adapter.meta.install_hint:
            err_console.print(f"[muted]Install with: {adapter.meta.install_hint}[/muted]")
        return
    except KeyboardInterrupt:
        console.print(f"\n[warn]✗ Cancelled[/warn] — stopped {adapter.meta.name}.")
        return

    storage.save_run(result)
    if result.ok:
        console.print(f"[ok]✓ Done[/ok] in {result.duration_s}s")
    else:
        console.print(f"[warn]⚠ Exit code {result.returncode}[/warn] ({result.duration_s}s)")
    if result.stdout.strip():
        console.print(result.stdout.rstrip())
    if result.stderr.strip():
        err_console.print(f"[muted]{result.stderr.rstrip()}[/muted]")


def install_one(name: str) -> bool:
    """Install an external tool (with confirmation). True if it ends up ready."""
    adapter = registry.get(name)
    if adapter is None:
        err_console.print(f"[err]Unknown tool:[/err] {name}")
        err_console.print("[muted]Run 'mrrobot tools' to see what's available.[/muted]")
        return False

    meta = adapter.meta
    if meta.builtin:
        console.print(f"[ok]'{meta.name}' is built into mrrobot; no install needed.[/ok]")
        return True
    if which(meta.binary):
        console.print(f"[ok]✓ '{meta.name}' is already installed.[/ok]")
        return True

    cmd = pick_install_cmd(meta)
    if cmd is None:
        err_console.print(
            f"[err]No available package manager to install '{meta.name}' automatically.[/err]"
        )
        if meta.install_hint:
            console.print(f"[muted]Install it manually with: {meta.install_hint}[/muted]")
        return False

    console.print(f"This will run: [bold]{' '.join(cmd)}[/bold]")
    if not typer.confirm("Continue?", default=True):
        return False

    try:
        proc = subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print(f"\n[warn]✗ Cancelled[/warn] — stopped installing {meta.name}.")
        return False
    if proc.returncode == 0:
        console.print(f"[ok]✓ '{meta.name}' installed successfully.[/ok]")
        return True
    err_console.print(f"[err]Installation failed (exit code {proc.returncode}).[/err]")
    return False


def install_all_missing() -> None:
    """Install every missing external tool in one go."""
    missing = [
        a for a in registry.all_adapters()
        if not a.meta.builtin and not which(a.meta.binary)
    ]
    if not missing:
        console.print("[ok]✓ No external tool is missing.[/ok]")
        return

    console.print(f"[bold]{len(missing)}[/bold] external tools are missing:\n")
    plan: list[tuple[ToolAdapter, list[str] | None]] = []
    for adapter in missing:
        cmd = pick_install_cmd(adapter.meta)
        shown = " ".join(cmd) if cmd else "(no package manager available — install it by hand)"
        console.print(f"  • {adapter.meta.name}: [muted]{shown}[/muted]")
        plan.append((adapter, cmd))

    if not typer.confirm(
        "\nInstall all the ones that can be installed automatically?", default=True
    ):
        console.print("[muted]Cancelled.[/muted]")
        return

    for adapter, cmd in plan:
        console.print(f"\n▶ {adapter.meta.name}…")
        if cmd is None:
            hint = adapter.meta.install_hint or "see the upstream repo"
            err_console.print(f"[warn]⚠ No package manager available. Manually: {hint}[/warn]")
            continue
        try:
            proc = subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print(
                f"\n[warn]✗ Cancelled[/warn] — stopped before installing {adapter.meta.name}."
            )
            return
        if proc.returncode == 0:
            console.print(f"[ok]✓ {adapter.meta.name} installed.[/ok]")
        else:
            err_console.print(
                f"[err]✗ {adapter.meta.name} failed (exit code {proc.returncode}).[/err]"
            )


def get_self_update_status(timeout: float = 6.0) -> tuple[bool, str | None, str | None]:
    """Is a newer mrrobot available? See core.updates.check_self_update."""
    return check_self_update(timeout=timeout)


def self_update() -> None:
    """Re-run the official installer to update mrrobot in place."""
    url = f"https://raw.githubusercontent.com/{SELF_REPO}/{SELF_BRANCH}/install.sh"
    console.print(f"\nRunning the installer: [bold]curl -fsSL {url} | bash[/bold]\n")
    try:
        proc = subprocess.run(["bash", "-c", f"curl -fsSL '{url}' | bash"])
    except KeyboardInterrupt:
        console.print("\n[warn]✗ Cancelled[/warn] — update not completed.")
        return
    if proc.returncode == 0:
        console.print("\n[ok]✓ Updated.[/ok] Restart mrrobot to use the new version.")
    else:
        err_console.print(f"\n[err]Update failed (exit code {proc.returncode}).[/err]")
