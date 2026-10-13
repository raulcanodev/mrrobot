"""subfinder adapter: PASSIVE subdomain discovery.

Uses public sources (certificate transparency, passive DNS, etc.) without
sending traffic to the target. Upstream: https://github.com/projectdiscovery/subfinder (MIT).
"""

from __future__ import annotations

from ...core.models import Category, Mode, TargetKind, ToolMeta
from ..base import ToolAdapter


class Subfinder(ToolAdapter):
    meta = ToolMeta(
        name="subfinder",
        category=Category.WEB,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.DOMAIN,
        summary="Enumerates a domain's subdomains from public sources.",
        binary="subfinder",
        repo="projectdiscovery/subfinder",
        version_cmd=["subfinder", "-version"],
        install_hint="brew install subfinder",
        install_cmds=[["brew", "install", "subfinder"]],
        license="MIT",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        return ["-silent", "-d", target]
