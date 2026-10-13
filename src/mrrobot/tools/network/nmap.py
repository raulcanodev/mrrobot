"""Nmap adapter: ACTIVE port and service scanning.

WARNING: Nmap sends packets to the target. It's an ACTIVE action and only
runs against targets within the authorized scope (see scope).
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
        summary="Discovers open ports and services on an authorized host.",
        binary="nmap",
        repo="nmap/nmap",
        version_cmd=["nmap", "--version"],
        install_hint="brew install nmap",
        install_cmds=[["brew", "install", "nmap"]],
        license="NPSL",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        # Modest default scan: top 1000 ports + version detection.
        # Keep a moderate pace (-T3) so we don't flood the target.
        extra = options.get("ports")
        args = ["-sV", "-T3"]
        if isinstance(extra, str) and extra:
            args += ["-p", extra]
        args.append(target)
        return args
