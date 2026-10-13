"""Ejecución de herramientas externas.

Orquestamos procesos existentes en lugar de reimplementar su lógica. El
runner es síncrono y sencillo, pero está aislado para poder añadir después
ejecución asíncrona o concurrente sin tocar el resto del core.
"""

from __future__ import annotations

import shutil
import subprocess
import time

from .models import RunResult, ToolMeta


class ToolNotInstalled(RuntimeError):
    pass


class NotAuthorized(PermissionError):
    """Se intentó una acción ACTIVA contra un objetivo fuera del alcance."""


def which(binary: str) -> str | None:
    return shutil.which(binary)


def run_tool(
    meta: ToolMeta,
    args: list[str],
    target: str,
    *,
    timeout: int = 300,
) -> RunResult:
    """Lanza la herramienta y devuelve un resultado normalizado.

    La comprobación de autorización se hace una capa más arriba (en el
    adaptador), de modo que el runner solo se ocupa de ejecutar.
    """
    binary = which(meta.binary)
    if binary is None:
        raise ToolNotInstalled(meta.binary)

    command = [binary, *args]
    start = time.time()
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\n[mrrobot] tiempo agotado tras {timeout}s"
        code = 124

    return RunResult(
        tool=meta.name,
        target=target,
        mode=meta.mode,
        command=command,
        returncode=code,
        stdout=stdout if isinstance(stdout, str) else "",
        stderr=stderr if isinstance(stderr, str) else "",
        started_at=start,
        duration_s=round(time.time() - start, 2),
    )
