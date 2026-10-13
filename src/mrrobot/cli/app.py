"""Punto de entrada de la CLI (Typer).

La CLI es una capa fina sobre el core: traduce comandos a llamadas del
registro/runner y presenta los resultados con Rich. Toda la lógica reutilizable
vive en mrrobot.core, de modo que mañana una TUI (Textual) pueda apoyarse en
exactamente lo mismo.
"""

from __future__ import annotations

import httpx
import typer
from rich.table import Table

from .. import __version__
from ..core import registry, storage
from ..core.config import SCOPE_FILE, load_scope, write_scope_template
from ..core.console import console, err_console
from ..core.models import Mode
from ..core.runner import NotAuthorized, ToolNotInstalled
from ..core.updates import check_tool
from .banner import render_banner

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="mrrobot — orquestador modular de OSINT y pentesting autorizado.",
    rich_markup_mode="rich",
)

scope_app = typer.Typer(help="Gestiona tu alcance autorizado (scope).")
tools_app = typer.Typer(help="Lista y comprueba el estado de las herramientas.")
app.add_typer(scope_app, name="scope")
app.add_typer(tools_app, name="tools")


# --------------------------------------------------------------------------- #
# Comprobación de herramientas / actualizaciones
# --------------------------------------------------------------------------- #
def _check_all(online: bool) -> list:
    statuses = []
    client = httpx.Client(timeout=6.0) if online else None
    try:
        for adapter in registry.all_adapters():
            statuses.append(check_tool(adapter.meta, online=online, client=client))
    finally:
        if client is not None:
            client.close()
    return statuses


def _print_startup_notices(online: bool) -> None:
    """Al arrancar: avisa de herramientas ausentes o con actualización disponible."""
    statuses = _check_all(online)
    missing = [s for s in statuses if not s.installed]
    updates = [s for s in statuses if s.update_available]

    if missing:
        names = ", ".join(s.meta.name for s in missing)
        console.print(f"[warn]⚠ No instaladas:[/warn] {names} "
                      f"[muted](usa 'mrrobot tools' para ver cómo instalarlas)[/muted]")
    if updates:
        for s in updates:
            console.print(
                f"[warn]↑ Actualización:[/warn] {s.meta.name} "
                f"{s.installed_version} → [ok]{s.latest_version}[/ok]"
            )
    if not missing and not updates and online:
        console.print("[ok]✓ Todas las herramientas integradas están al día.[/ok]")


# --------------------------------------------------------------------------- #
# Comandos
# --------------------------------------------------------------------------- #
@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Muestra la versión y sale."),
) -> None:
    if version:
        console.print(f"mrrobot v{__version__}")
        raise typer.Exit()
    # El banner lo dibuja cada comando que lo necesite (p.ej. 'doctor'),
    # para no repetirlo ni ensuciar la salida de 'run'/'history'.


@tools_app.callback(invoke_without_command=True)
def tools_list(
    ctx: typer.Context,
    online: bool = typer.Option(
        False, "--online/--offline",
        help="Consulta GitHub para comprobar si hay versiones más nuevas.",
    ),
) -> None:
    """Lista las herramientas integradas y su estado."""
    if ctx.invoked_subcommand is not None:
        return
    statuses = _check_all(online)
    table = Table(title="Herramientas integradas", title_style="brand", expand=True)
    table.add_column("Herramienta", style="bold")
    table.add_column("Categoría")
    table.add_column("Modo")
    table.add_column("Instalada")
    table.add_column("Versión")
    table.add_column("Última") if online else None

    for s in statuses:
        mode_style = "active" if s.meta.mode is Mode.ACTIVE else "passive"
        row = [
            s.meta.name,
            s.meta.category.value,
            f"[{mode_style}]{s.meta.mode.value}[/{mode_style}]",
            "[ok]sí[/ok]" if s.installed else "[err]no[/err]",
            s.installed_version or "—",
        ]
        if online:
            latest = s.latest_version or "—"
            if s.update_available:
                latest = f"[warn]{latest} ↑[/warn]"
            row.append(latest)
        table.add_row(*row)

    console.print(table)
    missing = [s for s in statuses if not s.installed]
    if missing:
        console.print("\n[muted]Sugerencias de instalación:[/muted]")
        for s in missing:
            hint = s.meta.install_hint or "ver repo upstream"
            console.print(f"  • {s.meta.name}: [muted]{hint}[/muted]")


@scope_app.command("init")
def scope_init() -> None:
    """Crea la plantilla de alcance autorizado y muestra su ruta."""
    path = write_scope_template()
    console.print(f"[ok]✓[/ok] Plantilla de alcance en: [bold]{path}[/bold]")
    console.print("[muted]Edítala con tus objetivos autorizados y pon authorized = true.[/muted]")


@scope_app.command("show")
def scope_show() -> None:
    """Muestra el alcance autorizado actual."""
    scope = load_scope()
    if not SCOPE_FILE.exists():
        console.print("[warn]Sin scope definido.[/warn] Ejecuta 'mrrobot scope init'.")
        raise typer.Exit()
    estado = "[ok]autorizado[/ok]" if scope.authorized else "[err]NO autorizado[/err]"
    console.print(f"Estado: {estado}")
    console.print(f"Dominios: {scope.domains or '—'}")
    console.print(f"Redes:    {scope.networks or '—'}")


@app.command()
def run(
    tool: str = typer.Argument(..., help="Nombre de la herramienta (ver 'mrrobot tools')."),
    target: str = typer.Argument(..., help="Objetivo: usuario, dominio o IP según la herramienta."),
    timeout: int = typer.Option(300, help="Tiempo máximo de ejecución en segundos."),
    ports: str = typer.Option("", help="Puertos para herramientas de red, p.ej. '1-1000'."),
) -> None:
    """Ejecuta una herramienta contra un objetivo."""
    adapter = registry.get(tool)
    if adapter is None:
        err_console.print(f"[err]Herramienta desconocida:[/err] {tool}")
        err_console.print("[muted]Usa 'mrrobot tools' para ver las disponibles.[/muted]")
        raise typer.Exit(code=2)

    scope = load_scope()
    mode = adapter.meta.mode
    label = "[active]ACTIVO[/active]" if mode is Mode.ACTIVE else "[passive]PASIVO[/passive]"
    console.print(f"▶ {adapter.meta.name} ({label}) → [bold]{target}[/bold]")

    try:
        with console.status("Ejecutando…", spinner="dots"):
            result = adapter.run(
                target, scope=scope, timeout=timeout,
                ports=ports or None,
            )
    except NotAuthorized as exc:
        err_console.print(f"[err]Bloqueado:[/err] {exc}")
        raise typer.Exit(code=3) from None
    except ToolNotInstalled as exc:
        err_console.print(f"[err]No instalada:[/err] {exc}")
        err_console.print(f"[muted]Instala con: {adapter.meta.install_hint}[/muted]")
        raise typer.Exit(code=4) from None

    storage.save_run(result)
    if result.ok:
        console.print(f"[ok]✓ Completado[/ok] en {result.duration_s}s")
    else:
        console.print(f"[warn]⚠ Código de salida {result.returncode}[/warn] ({result.duration_s}s)")
    if result.stdout.strip():
        console.print(result.stdout.rstrip())
    if result.stderr.strip():
        err_console.print(f"[muted]{result.stderr.rstrip()}[/muted]")


@app.command()
def history(limit: int = typer.Option(20, help="Número de ejecuciones a mostrar.")) -> None:
    """Muestra el historial de ejecuciones guardadas."""
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


@app.command()
def doctor(
    online: bool = typer.Option(
        True, "--online/--offline", help="Comprobar actualizaciones en red."
    ),
) -> None:
    """Chequeo de arranque: herramientas presentes y actualizaciones."""
    render_banner(__version__)
    _print_startup_notices(online)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
