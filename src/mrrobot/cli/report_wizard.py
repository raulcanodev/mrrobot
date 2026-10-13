"""Asistente interactivo para generar un informe completo.

Pregunta si se quiere generar el informe, sobre qué objetivo, qué tipo de
objetivo es y qué herramientas aplicables incluir (con un selector de
casillas, flechas + espacio); las ejecuta, imprime un resumen en consola y
ofrece guardar el detalle completo en un .txt.
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
from .style import QUESTIONARY_STYLE as _STYLE

_PREVIEW_LINES = 20

_KIND_WANTS: dict[str, set[TargetKind]] = {
    "dominio": {TargetKind.DOMAIN, TargetKind.HOST},
    "usuario": {TargetKind.USERNAME},
    "ip": {TargetKind.IP, TargetKind.HOST},
}


def _guess_kind(target: str) -> str:
    try:
        ipaddress.ip_address(target)
        return "ip"
    except ValueError:
        pass
    return "dominio" if "." in target else "usuario"


def run_wizard(target: str | None) -> None:
    if not questionary.confirm(
        "¿Quieres generar un informe completo ahora?", default=True, style=_STYLE
    ).ask():
        console.print("[muted]Cancelado.[/muted]")
        return

    if not target:
        target = questionary.text(
            "¿Sobre qué objetivo? (dominio, usuario o IP):", style=_STYLE
        ).ask()
    target = (target or "").strip()
    if not target:
        err_console.print("[err]No se indicó ningún objetivo.[/err]")
        return

    guess = _guess_kind(target)
    kinds = ["dominio", "usuario", "ip"]
    kind = questionary.select(
        "¿Qué es este objetivo?",
        choices=kinds,
        default=guess,
        style=_STYLE,
    ).ask()
    if kind is None:
        return

    candidates = [a for a in registry.all_adapters() if a.meta.target_kind in _KIND_WANTS[kind]]
    if not candidates:
        err_console.print("[err]No hay herramientas aplicables a ese tipo de objetivo.[/err]")
        return

    scope = load_scope()
    available = [a for a in candidates if a.meta.builtin or which(a.meta.binary)]
    missing = [a for a in candidates if a not in available]

    if not available:
        err_console.print("[err]Ninguna herramienta aplicable está instalada.[/err]")
        if missing:
            console.print("[muted]Instálalas con 'mrrobot tools install <nombre>'.[/muted]")
        return

    if missing:
        names = ", ".join(a.meta.name for a in missing)
        console.print(f"[muted]No instaladas (omitidas de la lista): {names}[/muted]\n")

    def _choice_label(adapter) -> str:
        is_active = adapter.meta.mode is Mode.ACTIVE
        mode_txt = "ACTIVO" if is_active else "pasivo"
        blocked = " — FUERA DE SCOPE" if is_active and not scope.allows(target) else ""
        return f"{adapter.meta.name} ({mode_txt}{blocked}) — {adapter.meta.summary}"

    chosen = questionary.checkbox(
        "¿Qué herramientas incluyo? (espacio para marcar/desmarcar, Enter para continuar)",
        choices=[
            questionary.Choice(_choice_label(a), value=a, checked=True) for a in available
        ],
        style=_STYLE,
    ).ask()

    if not chosen:
        err_console.print("[err]No se seleccionó ninguna herramienta.[/err]")
        return

    report = Report(target=target, kind=kind)
    console.print()
    for adapter in chosen:
        is_active = adapter.meta.mode is Mode.ACTIVE
        mode_label = "[active]ACTIVO[/active]" if is_active else "[passive]PASIVO[/passive]"
        console.print(f"▶ {adapter.meta.name} ({mode_label})… ", end="")
        try:
            with console.status("", spinner="dots"):
                result = adapter.run(target, scope=scope)
        except NotAuthorized:
            console.print("[err]bloqueada (fuera de scope)[/err]")
            report.sections.append(
                Section(
                    tool=adapter.meta.name,
                    mode=adapter.meta.mode,
                    status="blocked",
                    detail=(
                        "Bloqueada: el objetivo no está en tu alcance autorizado "
                        "('mrrobot scope init' para declararlo)."
                    ),
                )
            )
            continue
        except ToolNotInstalled:
            console.print("[err]no instalada[/err]")
            report.sections.append(
                Section(
                    tool=adapter.meta.name,
                    mode=adapter.meta.mode,
                    status="missing",
                    detail="No estaba instalada en el momento de ejecutar el informe.",
                )
            )
            continue

        storage.save_run(result)
        console.print("[ok]ok[/ok]" if result.ok else f"[warn]código {result.returncode}[/warn]")
        report.sections.append(
            Section(
                tool=adapter.meta.name,
                mode=adapter.meta.mode,
                status="ok" if result.ok else "fail",
                result=result,
            )
        )

    console.print()
    _print_summary(report)

    if questionary.confirm(
        "¿Guardar este informe completo en un archivo .txt?", default=True, style=_STYLE
    ).ask():
        path = save_report(report)
        console.print(f"[ok]✓ Informe guardado en:[/ok] {path}")
    else:
        console.print("[muted]Informe no guardado en disco (solo quedó en consola).[/muted]")


def _print_summary(report: Report) -> None:
    console.rule(f"[brand]Informe — {report.target} ({report.kind})[/brand]")
    for sec in report.sections:
        if sec.status == "ok":
            title = f"[ok]✓ {sec.tool}[/ok]"
        elif sec.status == "fail":
            title = f"[warn]⚠ {sec.tool}[/warn]"
        else:
            title = f"[err]✗ {sec.tool}[/err]"

        if sec.result is not None:
            # Si falló y no dejó nada en stdout, el motivo está en stderr
            # (p. ej. un adaptador integrado que reporta un error de red ahí).
            text = sec.result.stdout.rstrip()
            if not text and sec.status == "fail":
                text = sec.result.stderr.rstrip()
            all_lines = text.splitlines() or ["(sin salida)"]
            body = "\n".join(all_lines[:_PREVIEW_LINES])
            if len(all_lines) > _PREVIEW_LINES:
                remaining = len(all_lines) - _PREVIEW_LINES
                body += f"\n[muted]… +{remaining} líneas más (ver el .txt si lo guardas)[/muted]"
        else:
            body = sec.detail

        console.print(Panel(body, title=title, border_style="muted", expand=True))
