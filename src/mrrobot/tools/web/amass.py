"""OWASP Amass adapter in passive mode: attack-surface mapping.

A much more aggressive recon engine, source-wise, than subfinder (crosses
passive DNS, certificates, search-engine scraping and more providers). We
always constrain it to `-passive`: without that flag, Amass does active
DNS resolution against the target, which would turn it into an ACTIVE
action.
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
        summary="Attack-surface mapping: subdomains and assets via passive sources.",
        binary="amass",
        repo="owasp-amass/amass",
        version_cmd=["amass", "version"],
        install_hint="brew install amass",
        install_cmds=[["brew", "install", "amass"]],
        license="Apache-2.0",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        # -passive is mandatory here: without it, Amass resolves DNS
        # against the target and stops being a passive technique.
        return ["enum", "-passive", "-d", target]
