"""Data models shared across the whole project.

The core knows nothing about the CLI or any future interface: it just
defines clean structures that any layer (terminal, TUI, API) can reuse.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


class Category(enum.StrEnum):
    """Module categories, in the style of a classic recon-tool menu."""

    OSINT = "osint"
    NETWORK = "network"
    WEB = "web"
    UTILITIES = "utilities"


class Mode(enum.StrEnum):
    """A tool's execution profile.

    PASSIVE  -> only queries public sources, never touches the target.
    ACTIVE   -> sends traffic to the target; requires explicit scope authorization.
    """

    PASSIVE = "passive"
    ACTIVE = "active"


class TargetKind(enum.StrEnum):
    """What kind of target a tool expects.

    Used to filter which tools make sense to offer in the report wizard
    based on what the user is investigating. HOST accepts either a domain
    or an IP (e.g. nmap or a TLS handshake).
    """

    USERNAME = "username"
    DOMAIN = "domain"
    IP = "ip"
    HOST = "host"


@dataclass(frozen=True)
class ToolMeta:
    """Metadata for an external tool we orchestrate (never reimplement)."""

    name: str
    category: Category
    mode: Mode
    summary: str
    # What it expects as a target (domain, username, IP, or generic host).
    target_kind: TargetKind = TargetKind.DOMAIN
    # Binary we expect to find on the PATH. Empty if "builtin".
    binary: str = ""
    # True if mrrobot implements the logic in Python (no external binary):
    # always "installed" and needs no setup.
    builtin: bool = False
    # Upstream repo, used to check for updates.
    repo: str | None = None
    # Command to read the installed version, e.g. ["nmap", "--version"].
    version_cmd: list[str] = field(default_factory=list)
    # Human-readable install hint shown when the tool isn't present.
    install_hint: str | None = None
    # Candidate install commands, in order of preference. Each is an argv;
    # the first one whose package manager (first token) is on the PATH is
    # used. E.g. [["brew", "install", "nmap"]].
    install_cmds: list[list[str]] = field(default_factory=list)
    # Upstream license (we respect it: we run the tool, never redistribute its code).
    license: str | None = None


@dataclass
class ToolStatus:
    """Detected state of a tool on the user's machine."""

    meta: ToolMeta
    installed: bool
    path: str | None = None
    installed_version: str | None = None
    latest_version: str | None = None

    @property
    def update_available(self) -> bool:
        if not (self.installed_version and self.latest_version):
            return False
        from .updates import is_newer  # local import to avoid a cycle

        return is_newer(self.latest_version, self.installed_version)


@dataclass
class RunResult:
    """Normalized result of running a tool."""

    tool: str
    target: str
    mode: Mode
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    started_at: float = field(default_factory=time.time)
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.returncode == 0
