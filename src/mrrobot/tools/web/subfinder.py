"""Adaptador de subfinder: descubrimiento PASIVO de subdominios.

Usa fuentes públicas (transparencia de certificados, DNS pasivo, etc.) sin
enviar tráfico al objetivo. Upstream: https://github.com/projectdiscovery/subfinder (MIT).
"""

from __future__ import annotations

from ...core.models import Category, Mode, ToolMeta
from ..base import ToolAdapter


class Subfinder(ToolAdapter):
    meta = ToolMeta(
        name="subfinder",
        category=Category.WEB,
        mode=Mode.PASSIVE,
        summary="Enumera subdominios de un dominio a partir de fuentes públicas.",
        binary="subfinder",
        repo="projectdiscovery/subfinder",
        version_cmd=["subfinder", "-version"],
        install_hint="brew install subfinder  (o 'go install' desde el repo oficial)",
        license="MIT",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        return ["-silent", "-d", target]
