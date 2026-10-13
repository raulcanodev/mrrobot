"""Sherlock adapter: looks up a username across public profiles.

PASSIVE recon: it queries public websites, it doesn't attack a target.
Upstream: https://github.com/sherlock-project/sherlock (MIT).
"""

from __future__ import annotations

from ...core.models import Category, Mode, TargetKind, ToolMeta
from ..base import ToolAdapter


class Sherlock(ToolAdapter):
    meta = ToolMeta(
        name="sherlock",
        category=Category.OSINT,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.USERNAME,
        summary="Looks up a username across hundreds of public social networks.",
        binary="sherlock",
        repo="sherlock-project/sherlock",
        version_cmd=["sherlock", "--version"],
        install_hint="brew install sherlock",
        install_cmds=[["brew", "install", "sherlock"], ["pipx", "install", "sherlock-project"]],
        license="MIT",
    )

    def build_args(self, target: str, **options: object) -> list[str]:
        # --print-found: only matched profiles; --no-color for clean captured output.
        return [target, "--print-found", "--no-color"]
