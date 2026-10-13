"""Shared Rich console.

Centralizing the console here keeps the whole program visually consistent,
and lets a future interface swap out just this module.
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
