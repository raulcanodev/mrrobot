"""Adaptador de OWASP Amass en modo pasivo: mapeo de superficie de ataque.

Motor de reconocimiento mucho más agresivo en fuentes que subfinder (cruza
DNS pasivo, certificados, scraping de buscadores y más proveedores). Lo
limitamos siempre a `-passive`: sin esa bandera, Amass hace resolución DNS
activa contra el objetivo, y eso lo convertiría en una acción ACTIVA.
Upstream: https://github.com/owasp-amass/amass (Apache-2.0).
"""

from __future__ import annotations

from ...core.models import Category, Mode, TargetKind, ToolMeta
from ..base import ToolAdapter


class Amass(ToolAdapter):
    meta = ToolMeta(
        name="amass",
        category=Category.WEB,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.DOMAIN,
        summary="Mapeo de superficie de ataque: subdominios y activos vía fuentes pasivas.",
        binary="amass",
        repo="owasp-amass/amass",
        version_cmd=["amass", "version"],
        install_hint="brew install amass",
        install_cmds=[["brew", "install", "amass"]],
        license="Apache-2.0",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        # -passive es obligatorio aquí: sin él, Amass resuelve DNS contra
        # el objetivo y deja de ser una técnica pasiva.
        return ["enum", "-passive", "-d", target]
