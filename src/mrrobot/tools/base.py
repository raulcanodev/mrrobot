"""Adaptador base para herramientas externas.

Cada herramienta que integremos hereda de ToolAdapter y solo tiene que:
  1. Declarar sus metadatos (ToolMeta).
  2. Traducir una petición de alto nivel a los argumentos del binario.

La lógica común (autorización de scope, ejecución, normalización) vive aquí,
así que añadir una herramienta nueva son unas pocas líneas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.config import Scope
from ..core.models import Mode, RunResult, ToolMeta
from ..core.runner import NotAuthorized, run_tool


class ToolAdapter(ABC):
    meta: ToolMeta

    @abstractmethod
    def build_args(self, target: str, **options: object) -> list[str]:
        """Devuelve los argumentos de línea de comandos para el objetivo dado."""
        raise NotImplementedError

    def run(
        self,
        target: str,
        *,
        scope: Scope,
        timeout: int = 300,
        **options: object,
    ) -> RunResult:
        # Barrera de autorización: lo ACTIVO solo contra objetivos en alcance.
        if self.meta.mode is Mode.ACTIVE and not scope.allows(target):
            raise NotAuthorized(
                f"'{target}' no está en tu alcance autorizado. "
                f"La herramienta '{self.meta.name}' envía tráfico al objetivo "
                f"(modo ACTIVO) y requiere permiso explícito. "
                f"Ejecuta 'mrrobot scope init' y declara el objetivo."
            )
        args = self.build_args(target, **options)
        return run_tool(self.meta, args, target, timeout=timeout)
