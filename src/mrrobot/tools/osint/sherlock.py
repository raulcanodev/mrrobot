"""Adaptador de Sherlock: busca un nombre de usuario en perfiles públicos.

Es reconocimiento PASIVO: consulta sitios web públicos, no ataca un objetivo.
Upstream: https://github.com/sherlock-project/sherlock (MIT).
"""

from __future__ import annotations

from ...core.models import Category, Mode, ToolMeta
from ..base import ToolAdapter


class Sherlock(ToolAdapter):
    meta = ToolMeta(
        name="sherlock",
        category=Category.OSINT,
        mode=Mode.PASSIVE,
        summary="Busca un nombre de usuario en cientos de redes sociales públicas.",
        binary="sherlock",
        repo="sherlock-project/sherlock",
        version_cmd=["sherlock", "--version"],
        install_hint="pipx install sherlock-project",
        license="MIT",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        # --print-found: solo perfiles encontrados; --no-color para capturar salida limpia.
        return [target, "--print-found", "--no-color"]
