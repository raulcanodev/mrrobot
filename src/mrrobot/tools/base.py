"""Adaptador base para herramientas, externas o integradas.

Cada herramienta que integremos hereda de ToolAdapter. Hay dos formas de
implementarla:

  1. Externa (la mayoría): sobrescribe `build_args()` para traducir una
     petición de alto nivel a los argumentos del binario. `execute()` ya
     sabe lanzar el proceso con esos argumentos.
  2. Integrada ("builtin", sin binario externo, p. ej. una consulta a una
     API pública): sobrescribe `execute()` directamente y construye su
     propio `RunResult` con `make_result()`.

La lógica común (autorización de scope, medición de tiempo, normalización)
vive aquí, así que añadir una herramienta nueva son pocas líneas.
"""

from __future__ import annotations

import time
from abc import ABC

from ..core.config import Scope
from ..core.models import Mode, RunResult, ToolMeta
from ..core.runner import NotAuthorized, run_tool


def make_result(
    meta: ToolMeta,
    target: str,
    *,
    returncode: int,
    stdout: str,
    stderr: str,
    started_at: float,
    command: list[str] | None = None,
) -> RunResult:
    """Construye un RunResult uniforme para herramientas integradas."""
    return RunResult(
        tool=meta.name,
        target=target,
        mode=meta.mode,
        command=command or [f"(integrado) {meta.name}"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        started_at=started_at,
        duration_s=round(time.time() - started_at, 2),
    )


class ToolAdapter(ABC):
    meta: ToolMeta

    def build_args(self, target: str, **options: object) -> list[str]:
        """Traduce la petición a argumentos del binario. Solo para herramientas
        externas; las integradas sobrescriben execute() y no necesitan esto."""
        raise NotImplementedError(
            f"{type(self).__name__} no implementa build_args(); "
            "si es una herramienta integrada, sobrescribe execute()."
        )

    def execute(self, target: str, *, timeout: int = 300, **options: object) -> RunResult:
        """Ejecuta la herramienta y devuelve el resultado. Por defecto lanza
        el binario externo con build_args(); las integradas lo sobrescriben."""
        args = self.build_args(target, **options)
        return run_tool(self.meta, args, target, timeout=timeout)

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
        return self.execute(target, timeout=timeout, **options)
