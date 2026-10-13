"""Consola Rich compartida.

Centralizar la consola aquí hace que todo el programa tenga un estilo
coherente y que una futura interfaz pueda sustituir solo este módulo.
"""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

THEME = Theme(
    {
        "brand": "bold green",
        "muted": "grey58",
        "ok": "bold green",
        "warn": "bold yellow",
        "err": "bold red",
        "passive": "cyan",
        "active": "bold magenta",
    }
)

console = Console(theme=THEME)
err_console = Console(theme=THEME, stderr=True)
