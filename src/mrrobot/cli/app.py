"""Punto de entrada de la CLI (Typer).

La CLI es una capa fina sobre el core: traduce comandos a llamadas del
registro/runner y presenta los resultados con Rich. Toda la lógica reutilizable
vive en mrrobot.core (y en actions.py para lo compartido con el menú), de modo
que mañana una TUI (Textual) pueda apoyarse en exactamente lo mismo.

Sin argumentos, 'mrrobot' abre el menú interactivo (selector con flechas).
Cada acción del menú tiene también su comando directo — nunca es la única
forma de hacer algo.
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
    help="mrrobot — orquestador modular de OSINT y pentesting autorizado.",
    rich_markup_mode="rich",
)

scope_app = typer.Typer(help="Gestiona tu alcance autorizado (scope).")
tools_app = typer.Typer(help="Lista, comprueba e instala las herramientas.")
app.add_typer(scope_app, name="scope")
app.add_typer(tools_app, name="tools")


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Muestra la versión y sale."),
) -> None:
    if version:
        console.print(f"mrrobot v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        # Sin argumentos: menú interactivo. Con cualquier subcomando, la vía
        # manual de siempre (no se toca el comportamiento habitual).
        from .menu import main_menu

        main_menu()


@app.command("menu")
def menu_command() -> None:
    """Abre el menú interactivo (lo mismo que ejecutar 'mrrobot' sin nada más)."""
    from .menu import main_menu

    main_menu()


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
    actions.print_tools_table(online)


@tools_app.command("install")
def tools_install(
    name: str = typer.Argument(None, help="Nombre de la herramienta. Omite si usas --all."),
    all_missing: bool = typer.Option(
        False, "--all", help="Instala de una vez todas las herramientas externas que falten."
    ),
) -> None:
    """Instala una herramienta externa, o todas las que falten con --all."""
    if all_missing:
        actions.install_all_missing()
        return
    if not name:
        err_console.print("[err]Indica un nombre, o usa '--all' para instalarlas todas.[/err]")
        raise typer.Exit(code=2)
    ok = actions.install_one(name)
    raise typer.Exit(code=0 if ok else 1)


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
    actions.execute_tool(adapter, target, scope=scope, timeout=timeout, ports=ports or None)


@app.command()
def history(limit: int = typer.Option(20, help="Número de ejecuciones a mostrar.")) -> None:
    """Muestra el historial de ejecuciones guardadas."""
    actions.print_history(limit)


@app.command()
def report(
    target: str = typer.Argument(None, help="Dominio, usuario o IP. Si se omite, se pregunta."),
) -> None:
    """Asistente interactivo: elige herramientas y genera un informe completo."""
    render_banner(__version__)
    run_wizard(target)


@app.command()
def doctor(
    online: bool = typer.Option(
        True, "--online/--offline", help="Comprobar actualizaciones en red."
    ),
) -> None:
    """Chequeo de arranque: herramientas presentes y actualizaciones."""
    render_banner(__version__)
    actions.print_startup_notices(online)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
