"""Adaptador de Nmap: escaneo ACTIVO de puertos y servicios.

ATENCIÓN: Nmap envía paquetes al objetivo. Es una acción ACTIVA y por tanto
solo se ejecuta contra objetivos dentro del alcance autorizado (ver scope).
Upstream: https://github.com/nmap/nmap (NPSL).
"""

from __future__ import annotations

from ...core.models import Category, Mode, TargetKind, ToolMeta
from ..base import ToolAdapter


class Nmap(ToolAdapter):
    meta = ToolMeta(
        name="nmap",
        category=Category.NETWORK,
        mode=Mode.ACTIVE,
        target_kind=TargetKind.HOST,
        summary="Descubre puertos y servicios abiertos en un host autorizado.",
        binary="nmap",
        repo="nmap/nmap",
        version_cmd=["nmap", "--version"],
        install_hint="brew install nmap",
        install_cmds=[["brew", "install", "nmap"]],
        license="NPSL",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        # Escaneo por defecto comedido: top 1000 puertos + detección de versión.
        # Mantenemos el ritmo moderado (-T3) para no saturar al objetivo.
        extra = options.get("ports")
        args = ["-sV", "-T3"]
        if isinstance(extra, str) and extra:
            args += ["-p", extra]
        args.append(target)
        return args
