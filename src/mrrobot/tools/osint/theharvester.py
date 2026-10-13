"""Adaptador de theHarvester: emails, hosts y empleados vía fuentes públicas.

Agrega motores de búsqueda, certificados y otras fuentes OSINT para un
dominio. PASIVO: las fuentes que usamos por defecto (-b all) no envían
tráfico directo al objetivo, consultan terceros sobre él.
Upstream: https://github.com/laramies/theHarvester (GPL-3.0).
"""

from __future__ import annotations

from ...core.models import Category, Mode, TargetKind, ToolMeta
from ..base import ToolAdapter


class TheHarvester(ToolAdapter):
    meta = ToolMeta(
        name="theharvester",
        category=Category.OSINT,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.DOMAIN,
        summary="Emails, subdominios y empleados de una organización vía fuentes OSINT públicas.",
        binary="theHarvester",
        repo="laramies/theHarvester",
        version_cmd=["theHarvester", "--version"],
        install_hint="brew install theharvester",
        install_cmds=[["brew", "install", "theharvester"]],
        license="GPL-3.0",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        sources = options.get("sources") or "all"
        return ["-d", target, "-b", str(sources)]
