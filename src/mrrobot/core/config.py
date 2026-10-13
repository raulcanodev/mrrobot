"""Configuración y control de alcance (scope) / autorización.

Esta es la pieza que distingue un launcher responsable de un simple wrapper:
antes de ejecutar nada ACTIVO contra un objetivo, mrrobot exige que ese
objetivo esté dentro de un alcance autorizado. El reconocimiento PASIVO
(fuentes públicas) se permite por defecto, pero también queda registrado.
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
    """Objetivos que el usuario declara estar autorizado a analizar activamente."""

    # Dominios/host exactos o con comodín de subdominio: "*.midominio.com".
    domains: list[str] = field(default_factory=list)
    # Redes/IPs en notación CIDR o IP suelta.
    networks: list[str] = field(default_factory=list)
    # Si el usuario firma la nota de autorización. Las acciones ACTIVAS la exigen.
    authorized: bool = False

    def allows(self, target: str) -> bool:
        """¿El objetivo entra dentro del alcance autorizado?"""
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
    """Carga el alcance desde ~/.config/mrrobot/scope.toml (si existe)."""
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
# Alcance autorizado de mrrobot
# -----------------------------
# Rellena SOLO con objetivos sobre los que tengas permiso explícito para
# realizar pruebas activas (equipos propios, laboratorios, programas de
# bug bounty dentro de su alcance, o clientes con autorización por escrito).
#
# Pon authorized = true para confirmar que tienes ese permiso. Sin ello,
# mrrobot bloqueará cualquier acción ACTIVA contra estos objetivos.

[scope]
authorized = false
domains = [
    # "midominio.com",
    # "*.laboratorio.local",
]
networks = [
    # "127.0.0.1/32",
    # "192.168.1.0/24",
]
"""


def write_scope_template() -> Path:
    """Crea una plantilla de scope si aún no existe y devuelve su ruta."""
    ensure_dirs()
    if not SCOPE_FILE.exists():
        SCOPE_FILE.write_text(SCOPE_TEMPLATE, encoding="utf-8")
    return SCOPE_FILE
