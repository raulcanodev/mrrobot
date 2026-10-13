"""Banner e identidad visual del arranque."""

from __future__ import annotations

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from ..core.console import console

_ART = r"""
 __  __ _____    _____ ___  ___  ___ _____
|  \/  |  __ \  |  __ \ _ \| _ )/ _ \_   _|
| |\/| | |__) | | |__) | // | _ \ (_) || |
|_|  |_|  _  /  |  _  /_|_\|___/\___/ |_|
      | | \ \   | | \ \
      |_|  \_\  |_|  \_\
"""


def render_banner(version: str) -> None:
    art = Text(_ART, style="brand")
    subtitle = Text("OSINT & Security Toolkit", style="muted")
    version_line = Text(f"v{version}", style="muted")
    body = Align.center(Text.assemble(art, "\n", subtitle, "  ", version_line))
    console.print(Panel(body, border_style="brand", padding=(0, 2)))
