"""Acciones compartidas entre los comandos directos y el menú interactivo.

Tanto `mrrobot run ...` como el menú con selector llaman exactamente a las
mismas funciones de aquí, así que nunca hay dos implementaciones de lo mismo
ni un camino que haga algo distinto del otro.
"""

from __future__ import annotations

import subprocess

import httpx
import typer
from rich.table import Table

from ..core import registry, storage
from ..core.config import Scope
from ..core.console import console, err_console
from ..core.installer import pick_install_cmd
from ..core.models import Mode, ToolStatus
from ..core.runner import NotAuthorized, ToolNotInstalled, which
from ..core.updates import check_tool
from ..tools.base import ToolAdapter


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
    """Al arrancar: avisa de herramientas ausentes o con actualización disponible."""
    statuses = check_all(online)
    missing = [s for s in statuses if not s.installed]
    updates = [s for s in statuses if s.update_available]

    if missing:
        names = ", ".join(s.meta.name for s in missing)
        console.print(
            f"[warn]⚠ No instaladas:[/warn] {names} "
            f"[muted](usa 'mrrobot tools install --all' para instalarlas)[/muted]"
        )
    if updates:
        for s in updates:
            console.print(
                f"[warn]↑ Actualización:[/warn] {s.meta.name} "
                f"{s.installed_version} → [ok]{s.latest_version}[/ok]"
            )
    if not missing and not updates and online:
        console.print("[ok]✓ Todas las herramientas integradas están al día.[/ok]")


def print_tools_table(online: bool) -> list[ToolStatus]:
    """Imprime la tabla de herramientas y devuelve las que faltan instalar."""
    statuses = sorted(check_all(online), key=lambda s: (s.meta.category.value, s.meta.name))
    table = Table(title="Herramientas integradas", title_style="brand", expand=True)
    table.add_column("Herramienta", style="bold")
    table.add_column("Categoría")
    table.add_column("Modo")
    table.add_column("Instalada")
    table.add_column("Versión")
    if online:
        table.add_column("Última")

    for s in statuses:
        mode_style = "active" if s.meta.mode is Mode.ACTIVE else "passive"
        version = "integrado" if s.meta.builtin else (s.installed_version or "—")
        row = [
            s.meta.name,
            s.meta.category.value,
            f"[{mode_style}]{s.meta.mode.value}[/{mode_style}]",
            "[ok]sí[/ok]" if s.installed else "[err]no[/err]",
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
            "\n[muted]Instálalas con 'mrrobot tools install <nombre>' "
            "(o '--all' para todas), o manualmente:[/muted]"
        )
        for s in missing:
            hint = s.meta.install_hint or "ver repo upstream"
            console.print(f"  • {s.meta.name}: [muted]{hint}[/muted]")
    return missing


def print_history(limit: int) -> None:
    rows = storage.recent_runs(limit)
    if not rows:
        console.print("[muted]Sin ejecuciones registradas todavía.[/muted]")
        return
    table = Table(title="Historial", title_style="brand")
    table.add_column("#")
    table.add_column("Herramienta")
    table.add_column("Objetivo")
    table.add_column("Modo")
    table.add_column("Salida")
    table.add_column("Dur. (s)")
    for r in rows:
        table.add_row(
            str(r["id"]), r["tool"], r["target"], r["mode"],
            str(r["returncode"]), str(r["duration_s"]),
        )
    console.print(table)
    console.print(f"[muted]Base de datos: {storage.db_location()}[/muted]")


def execute_tool(
    adapter: ToolAdapter,
    target: str,
    *,
    scope: Scope,
    timeout: int = 300,
    **options: object,
) -> None:
    """Ejecuta una herramienta y muestra el resultado. Usado por 'run' y el menú."""
    mode = adapter.meta.mode
    label = "[active]ACTIVO[/active]" if mode is Mode.ACTIVE else "[passive]PASIVO[/passive]"
    console.print(f"▶ {adapter.meta.name} ({label}) → [bold]{target}[/bold]")

    try:
        with console.status("Ejecutando…", spinner="dots"):
            result = adapter.run(target, scope=scope, timeout=timeout, **options)
    except NotAuthorized as exc:
        err_console.print(f"[err]Bloqueado:[/err] {exc}")
        return
    except ToolNotInstalled as exc:
        err_console.print(f"[err]No instalada:[/err] {exc}")
        if adapter.meta.install_hint:
            err_console.print(f"[muted]Instala con: {adapter.meta.install_hint}[/muted]")
        return

    storage.save_run(result)
    if result.ok:
        console.print(f"[ok]✓ Completado[/ok] en {result.duration_s}s")
    else:
        console.print(f"[warn]⚠ Código de salida {result.returncode}[/warn] ({result.duration_s}s)")
    if result.stdout.strip():
        console.print(result.stdout.rstrip())
    if result.stderr.strip():
        err_console.print(f"[muted]{result.stderr.rstrip()}[/muted]")


def install_one(name: str) -> bool:
    """Instala una herramienta externa (con confirmación). True si quedó lista."""
    adapter = registry.get(name)
    if adapter is None:
        err_console.print(f"[err]Herramienta desconocida:[/err] {name}")
        err_console.print("[muted]Usa 'mrrobot tools' para ver las disponibles.[/muted]")
        return False

    meta = adapter.meta
    if meta.builtin:
        console.print(f"[ok]'{meta.name}' es integrada en mrrobot; no requiere instalación.[/ok]")
        return True
    if which(meta.binary):
        console.print(f"[ok]✓ '{meta.name}' ya está instalada.[/ok]")
        return True

    cmd = pick_install_cmd(meta)
    if cmd is None:
        err_console.print(
            f"[err]No encuentro un gestor de paquetes disponible para instalar '{meta.name}'.[/err]"
        )
        if meta.install_hint:
            console.print(f"[muted]Instálala manualmente con: {meta.install_hint}[/muted]")
        return False

    console.print(f"Se ejecutará: [bold]{' '.join(cmd)}[/bold]")
    if not typer.confirm("¿Continuar?", default=True):
        return False

    proc = subprocess.run(cmd)
    if proc.returncode == 0:
        console.print(f"[ok]✓ '{meta.name}' instalada correctamente.[/ok]")
        return True
    err_console.print(f"[err]La instalación falló (código {proc.returncode}).[/err]")
    return False


def install_all_missing() -> None:
    """Instala de una vez todas las herramientas externas que falten."""
    missing = [
        a for a in registry.all_adapters()
        if not a.meta.builtin and not which(a.meta.binary)
    ]
    if not missing:
        console.print("[ok]✓ No falta ninguna herramienta externa por instalar.[/ok]")
        return

    console.print(f"Faltan [bold]{len(missing)}[/bold] herramientas externas:\n")
    plan: list[tuple[ToolAdapter, list[str] | None]] = []
    for adapter in missing:
        cmd = pick_install_cmd(adapter.meta)
        shown = " ".join(cmd) if cmd else "(sin gestor disponible — instálala a mano)"
        console.print(f"  • {adapter.meta.name}: [muted]{shown}[/muted]")
        plan.append((adapter, cmd))

    if not typer.confirm("\n¿Instalar todas las que se puedan automáticamente?", default=True):
        console.print("[muted]Cancelado.[/muted]")
        return

    for adapter, cmd in plan:
        console.print(f"\n▶ {adapter.meta.name}…")
        if cmd is None:
            hint = adapter.meta.install_hint or "ver repo upstream"
            err_console.print(f"[warn]⚠ Sin gestor disponible. Manualmente: {hint}[/warn]")
            continue
        proc = subprocess.run(cmd)
        if proc.returncode == 0:
            console.print(f"[ok]✓ {adapter.meta.name} instalada.[/ok]")
        else:
            err_console.print(f"[err]✗ {adapter.meta.name} falló (código {proc.returncode}).[/err]")
