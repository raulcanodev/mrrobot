"""Configuration and scope / authorization control.

This is the piece that sets a responsible launcher apart from a plain
wrapper: before running anything ACTIVE against a target, mrrobot requires
that target to be inside an authorized scope. PASSIVE recon (public
sources) is allowed by default, but it is still logged.
"""

from __future__ import annotations

import ipaddress
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "mrrobot"

CONFIG_DIR = Path(user_config_dir(APP_NAME))
DATA_DIR = Path(user_data_dir(APP_NAME))
SCOPE_FILE = CONFIG_DIR / "scope.toml"


@dataclass
class Scope:
    """Targets the user declares they're authorized to actively test."""

    # Exact domains/hosts or a subdomain wildcard: "*.mydomain.com".
    domains: list[str] = field(default_factory=list)
    # Networks/IPs in CIDR notation or a bare IP.
    networks: list[str] = field(default_factory=list)
    # Whether the user signed off on the authorization note. ACTIVE actions require it.
    authorized: bool = False

    def allows(self, target: str) -> bool:
        """Is this target within the authorized scope?"""
        if not self.authorized:
            return False
        return self._matches_domain(target) or self._matches_network(target)

    def _matches_domain(self, target: str) -> bool:
        host = target.lower().strip().rstrip(".")
        for pattern in self.domains:
            pattern = pattern.lower().strip().rstrip(".")
            if pattern == host:
                return True
            if pattern.startswith("*.") and host.endswith(pattern[1:]):
                return True
        return False

    def _matches_network(self, target: str) -> bool:
        try:
            ip = ipaddress.ip_address(target)
        except ValueError:
            return False
        for net in self.networks:
            try:
                if ip in ipaddress.ip_network(net, strict=False):
                    return True
            except ValueError:
                continue
        return False


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_scope() -> Scope:
    """Load the scope from ~/.config/mrrobot/scope.toml (if it exists)."""
    if not SCOPE_FILE.exists():
        return Scope()
    with SCOPE_FILE.open("rb") as fh:
        data = tomllib.load(fh)
    s = data.get("scope", {})
    return Scope(
        domains=list(s.get("domains", [])),
        networks=list(s.get("networks", [])),
        authorized=bool(s.get("authorized", False)),
    )


SCOPE_TEMPLATE = """\
# mrrobot authorized scope
# -------------------------
# Fill this in ONLY with targets you have explicit permission to actively
# test (your own systems, labs, bug bounty programs within their scope, or
# clients with written authorization).
#
# Set authorized = true to confirm you have that permission. Without it,
# mrrobot will block any ACTIVE action against these targets.

[scope]
authorized = false
domains = [
    # "mydomain.com",
    # "*.lab.local",
]
networks = [
    # "127.0.0.1/32",
    # "192.168.1.0/24",
]
"""


def write_scope_template() -> Path:
    """Create a scope template if one doesn't exist yet and return its path."""
    ensure_dirs()
    if not SCOPE_FILE.exists():
        SCOPE_FILE.write_text(SCOPE_TEMPLATE, encoding="utf-8")
    return SCOPE_FILE
