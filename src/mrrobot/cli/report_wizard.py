"""Interactive wizard to generate a full report.

Asks whether to generate the report, against which target, what kind of
target it is, and which applicable tools to include (via a checkbox
selector, arrows + space); runs them, prints a console summary, and
offers to save the full detail to a .txt file.
"""

from __future__ import annotations

import ipaddress

import questionary
from rich.panel import Panel

from ..core import registry, storage
from ..core.config import load_scope
from ..core.console import console, err_console
from ..core.models import Mode, TargetKind
from ..core.report import Report, Section, save_report
from ..core.runner import NotAuthorized, ToolNotInstalled, which
from . import actions
from .style import QUESTIONARY_STYLE as _STYLE

_PREVIEW_LINES = 20

_KIND_WANTS: dict[str, set[TargetKind]] = {
    "domain": {TargetKind.DOMAIN, TargetKind.HOST},
    "username": {TargetKind.USERNAME},
    "ip": {TargetKind.IP, TargetKind.HOST},
}


def _guess_kind(target: str) -> str:
    try:
        ipaddress.ip_address(target)
        return "ip"
    except ValueError:
        pass
    return "domain" if "." in target else "username"


def run_wizard(target: str | None) -> None:
    if not questionary.confirm(
        "Generate a full report now?", default=True, style=_STYLE
    ).ask():
        console.print("[muted]Cancelled.[/muted]")
        return

    if not target:
        target = questionary.text(
            "Which target? (domain, username or IP):", style=_STYLE
        ).ask()
    target = (target or "").strip()
    if not target:
        err_console.print("[err]No target given.[/err]")
        return

    guess = _guess_kind(target)
    kinds = ["domain", "username", "ip"]
    kind = questionary.select(
        "What kind of target is this?",
        choices=kinds,
        default=guess,
        style=_STYLE,
    ).ask()
    if kind is None:
        return

    candidates = [a for a in registry.all_adapters() if a.meta.target_kind in _KIND_WANTS[kind]]
    if not candidates:
        err_console.print("[err]No tools apply to this kind of target.[/err]")
        return

    scope = load_scope()
    available = [a for a in candidates if a.meta.builtin or which(a.meta.binary)]
    missing = [a for a in candidates if a not in available]

    if not available:
        err_console.print("[err]No applicable tool is installed.[/err]")
        if missing:
            console.print("[muted]Install them with 'mrrobot tools install <name>'.[/muted]")
        return

    if missing:
        names = ", ".join(a.meta.name for a in missing)
        console.print(f"[muted]Not installed (left out of the list): {names}[/muted]\n")

    def _choice_label(adapter) -> str:
        is_active = adapter.meta.mode is Mode.ACTIVE
        mode_txt = "ACTIVE" if is_active else "passive"
        blocked = " — OUT OF SCOPE" if is_active and not scope.allows(target) else ""
        return f"{adapter.meta.name} ({mode_txt}{blocked}) — {adapter.meta.summary}"

    chosen = questionary.checkbox(
        "Which tools should I include? (space to toggle, Enter to continue)",
        choices=[
            questionary.Choice(_choice_label(a), value=a, checked=True) for a in available
        ],
        style=_STYLE,
    ).ask()

    if not chosen:
        err_console.print("[err]No tool was selected.[/err]")
        return

    report = Report(target=target, kind=kind)
    console.print()
    total = len(chosen)
    for i, adapter in enumerate(chosen, start=1):
        is_active = adapter.meta.mode is Mode.ACTIVE
        mode_label = "[active]ACTIVE[/active]" if is_active else "[passive]passive[/passive]"
        step = f"[{i}/{total}]"
        try:
            result = actions.run_with_progress(
                f"{step} Running {adapter.meta.name} ({mode_label})…",
                lambda a=adapter: a.run(target, scope=scope),
            )
        except NotAuthorized:
            console.print(f"[err]✗ {step} {adapter.meta.name} — blocked (out of scope)[/err]")
            report.sections.append(
                Section(
                    tool=adapter.meta.name,
                    mode=adapter.meta.mode,
                    status="blocked",
                    detail=(
                        "Blocked: the target is not in your authorized scope "
                        "('mrrobot scope init' to declare it)."
                    ),
                )
            )
            continue
        except ToolNotInstalled:
            console.print(f"[err]✗ {step} {adapter.meta.name} — not installed[/err]")
            report.sections.append(
                Section(
                    tool=adapter.meta.name,
                    mode=adapter.meta.mode,
                    status="missing",
                    detail="It wasn't installed when the report ran.",
                )
            )
            continue
        except KeyboardInterrupt:
            remaining = total - i + 1
            console.print(
                f"\n[warn]✗ Cancelled[/warn] — stopped {adapter.meta.name}, "
                f"skipping the remaining {remaining} tool(s)."
            )
            break

        storage.save_run(result)
        if result.ok:
            console.print(f"[ok]✓ {step} {adapter.meta.name}[/ok] — {result.duration_s}s")
        else:
            console.print(
                f"[warn]⚠ {step} {adapter.meta.name}[/warn] "
                f"— exit code {result.returncode} ({result.duration_s}s)"
            )
        report.sections.append(
            Section(
                tool=adapter.meta.name,
                mode=adapter.meta.mode,
                status="ok" if result.ok else "fail",
                result=result,
            )
        )

    console.print()
    if not report.sections:
        console.print("[muted]Nothing to show — cancelled before any tool finished.[/muted]")
        return

    _print_summary(report)

    if questionary.confirm(
        "Save this full report to a .txt file?", default=True, style=_STYLE
    ).ask():
        path = save_report(report)
        console.print(f"[ok]✓ Report saved to:[/ok] {path}")
    else:
        console.print("[muted]Report not saved to disk (console only).[/muted]")


def _print_summary(report: Report) -> None:
    console.rule(f"[brand]Report — {report.target} ({report.kind})[/brand]")
    for sec in report.sections:
        if sec.status == "ok":
            title = f"[ok]✓ {sec.tool}[/ok]"
        elif sec.status == "fail":
            title = f"[warn]⚠ {sec.tool}[/warn]"
        else:
            title = f"[err]✗ {sec.tool}[/err]"

        if sec.result is not None:
            # If it failed and left nothing in stdout, the reason is in
            # stderr (e.g. a built-in adapter reporting a network error there).
            text = sec.result.stdout.rstrip()
            if not text and sec.status == "fail":
                text = sec.result.stderr.rstrip()
            all_lines = text.splitlines() or ["(no output)"]
            body = "\n".join(all_lines[:_PREVIEW_LINES])
            if len(all_lines) > _PREVIEW_LINES:
                remaining = len(all_lines) - _PREVIEW_LINES
                body += f"\n[muted]… +{remaining} more lines (see the saved .txt)[/muted]"
        else:
            body = sec.detail

        console.print(Panel(body, title=title, border_style="muted", expand=True))
