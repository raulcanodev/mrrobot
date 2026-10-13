"""theHarvester adapter: emails, hosts and employees via public sources.

Aggregates search engines, certificates and other OSINT sources for a
domain. PASSIVE: the default sources (-b all) don't send traffic directly
to the target, they query third parties about it.
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
        summary="Emails, subdomains and employees of an organization via public OSINT sources.",
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
