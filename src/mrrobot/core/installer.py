"""Resuelve cómo instalar automáticamente una herramienta externa.

Cada ToolMeta declara varios comandos candidatos en orden de preferencia
(p. ej. brew antes que pip). Aquí solo elegimos el primero cuyo gestor de
paquetes ya esté disponible; la propia CLI es quien pide confirmación y
ejecuta el comando con la salida visible para el usuario.
"""

from __future__ import annotations

from .models import ToolMeta
from .runner import which


def pick_install_cmd(meta: ToolMeta) -> list[str] | None:
    """Primer comando de instalación cuyo gestor de paquetes está en el PATH."""
    for cmd in meta.install_cmds:
        if cmd and which(cmd[0]):
            return cmd
    return None
