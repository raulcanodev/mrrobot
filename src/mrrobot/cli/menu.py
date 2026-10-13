"""Menú interactivo: navegación con flechas, sin perder la vía manual.

Se abre al ejecutar 'mrrobot' sin argumentos (o con 'mrrobot menu'). Cada
opción de aquí tiene también su comando directo documentado en 'mrrobot
--help' — el menú solo es una forma más cómoda de llegar a lo mismo.
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

_VOLVER = "‹ Volver"

_TARGET_HINTS = {
    TargetKind.USERNAME: "usuario",
    TargetKind.DOMAIN: "dominio",
    TargetKind.IP: "dirección IP",
    TargetKind.HOST: "dominio o IP",
}

_MAIN_CHOICES = [
    "Ejecutar una herramienta",
    "Generar informe completo",
    "Ver estado de herramientas",
    "Instalar herramientas que falten",
    "Gestionar alcance (scope)",
    "Ver historial",
    "Salir",
]


def main_menu() -> None:
    if not sys.stdin.isatty():
        console.print(
            "[muted]No hay una terminal interactiva disponible; "
            "usa comandos directos ('mrrobot --help').[/muted]"
        )
        return

    render_banner(__version__)
    console.print(
        "[muted]↑/↓ para moverte, Enter para elegir. "
        "También puedes usar comandos directos: 'mrrobot --help'.[/muted]\n"
    )

    try:
        while True:
            choice = questionary.select(
                "¿Qué quieres hacer?", choices=_MAIN_CHOICES, style=_STYLE
            ).ask()
            if choice is None or choice == "Salir":
                console.print("[muted]Hasta luego.[/muted]")
                return

            console.print()
            if choice == "Ejecutar una herramienta":
                _run_tool_flow()
            elif choice == "Generar informe completo":
                run_wizard(None)
            elif choice == "Ver estado de herramientas":
                actions.print_tools_table(online=False)
            elif choice == "Instalar herramientas que falten":
                actions.install_all_missing()
            elif choice == "Gestionar alcance (scope)":
                _scope_flow()
            elif choice == "Ver historial":
                actions.print_history(20)
            console.print()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[muted]Hasta luego.[/muted]")


def _run_tool_flow() -> None:
    adapters = sorted(registry.all_adapters(), key=lambda a: (a.meta.category.value, a.meta.name))
    labels = [
        f"{a.meta.name}  ({a.meta.category.value}/{a.meta.mode.value}) — {a.meta.summary}"
        for a in adapters
    ]
    choice = questionary.select(
        "¿Qué herramienta quieres ejecutar?",
        choices=[*labels, _VOLVER],
        style=_STYLE,
    ).ask()
    if choice is None or choice == _VOLVER:
        return

    adapter = adapters[labels.index(choice)]
    hint = _TARGET_HINTS[adapter.meta.target_kind]
    target = questionary.text(f"Objetivo ({hint}):", style=_STYLE).ask()
    if not target or not target.strip():
        return
    target = target.strip()

    extra: dict[str, object] = {}
    if adapter.meta.name == "nmap":
        ports = questionary.text(
            "Puertos (opcional, p.ej. '1-1000'; Enter para el escaneo por defecto):",
            style=_STYLE,
        ).ask()
        extra["ports"] = ports.strip() if ports else None

    scope = load_scope()
    actions.execute_tool(adapter, target, scope=scope, **extra)


def _scope_flow() -> None:
    choice = questionary.select(
        "Alcance autorizado",
        choices=["Ver estado actual", "Crear/abrir plantilla", _VOLVER],
        style=_STYLE,
    ).ask()
    if choice is None or choice == _VOLVER:
        return
    if choice == "Ver estado actual":
        if not SCOPE_FILE.exists():
            console.print("[warn]Sin scope definido todavía.[/warn]")
            return
        scope = load_scope()
        estado = "[ok]autorizado[/ok]" if scope.authorized else "[err]NO autorizado[/err]"
        console.print(f"Estado: {estado}")
        console.print(f"Dominios: {scope.domains or '—'}")
        console.print(f"Redes:    {scope.networks or '—'}")
    elif choice == "Crear/abrir plantilla":
        path = write_scope_template()
        console.print(f"[ok]✓[/ok] Plantilla en: [bold]{path}[/bold]")
        console.print("[muted]Edítala a mano y pon authorized = true.[/muted]")
