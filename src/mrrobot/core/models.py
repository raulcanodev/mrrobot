"""Modelos de datos compartidos por todo el proyecto.

El core no sabe nada de la CLI ni de una futura interfaz: solo define
estructuras limpias que cualquier capa (terminal, TUI, API) puede reutilizar.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


class Category(enum.StrEnum):
    """Categorías de los módulos, al estilo de un menú clásico de recon."""

    OSINT = "osint"
    NETWORK = "network"
    WEB = "web"
    UTILITIES = "utilities"


class Mode(enum.StrEnum):
    """Perfil de ejecución de una herramienta.

    PASSIVE  -> solo consulta fuentes públicas, no toca el objetivo.
    ACTIVE   -> envía tráfico al objetivo; exige autorización/scope explícito.
    """

    PASSIVE = "passive"
    ACTIVE = "active"


@dataclass(frozen=True)
class ToolMeta:
    """Metadatos de una herramienta externa que orquestamos (no reimplementamos)."""

    name: str
    category: Category
    mode: Mode
    summary: str
    # Binario que esperamos encontrar en el PATH.
    binary: str
    # Repositorio upstream, usado para comprobar actualizaciones.
    repo: str | None = None
    # Comando para leer la versión instalada, p.ej. ["nmap", "--version"].
    version_cmd: list[str] = field(default_factory=list)
    # Pista de instalación que mostramos si la herramienta no está presente.
    install_hint: str | None = None
    # Licencia upstream (respetamos: ejecutamos, no redistribuimos su código).
    license: str | None = None


@dataclass
class ToolStatus:
    """Estado detectado de una herramienta en la máquina del usuario."""

    meta: ToolMeta
    installed: bool
    path: str | None = None
    installed_version: str | None = None
    latest_version: str | None = None

    @property
    def update_available(self) -> bool:
        if not (self.installed_version and self.latest_version):
            return False
        from .updates import is_newer  # import local para evitar ciclos

        return is_newer(self.latest_version, self.installed_version)


@dataclass
class RunResult:
    """Resultado normalizado de ejecutar una herramienta."""

    tool: str
    target: str
    mode: Mode
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    started_at: float = field(default_factory=time.time)
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.returncode == 0
