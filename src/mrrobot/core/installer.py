"""Works out how to automatically install an external tool.

Each ToolMeta declares several candidate commands in order of preference
(e.g. brew before pip). Here we just pick the first one whose package
manager is already available; the CLI itself asks for confirmation and
runs the command with output visible to the user.
"""

from __future__ import annotations

from .models import ToolMeta
from .runner import which


def pick_install_cmd(meta: ToolMeta) -> list[str] | None:
    """First install command whose package manager is on the PATH."""
    for cmd in meta.install_cmds:
        if cmd and which(cmd[0]):
            return cmd
    return None
