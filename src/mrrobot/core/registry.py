"""Registro central de herramientas.

Un único punto donde se listan los adaptadores disponibles. Añadir una
herramienta nueva es: crear su adaptador y registrarlo aquí. La CLI y
cualquier futura interfaz consultan solo este registro.
"""

from __future__ import annotations

from ..tools.base import ToolAdapter
from ..tools.network.certinfo import CertInfo
from ..tools.network.internetdb import InternetDB
from ..tools.network.nmap import Nmap
from ..tools.osint.sherlock import Sherlock
from ..tools.osint.theharvester import TheHarvester
from ..tools.osint.whois_lookup import Whois
from ..tools.web.amass import Amass
from ..tools.web.crtsh import CrtSh
from ..tools.web.subfinder import Subfinder
from ..tools.web.wayback import Wayback
from .models import Category

# Instancias de los adaptadores integrados.
_ADAPTERS: list[ToolAdapter] = [
    # OSINT
    Sherlock(),
    TheHarvester(),
    Whois(),
    # Web / dominios
    Subfinder(),
    Amass(),
    CrtSh(),
    Wayback(),
    # Red
    Nmap(),
    InternetDB(),
    CertInfo(),
]

_BY_NAME: dict[str, ToolAdapter] = {a.meta.name: a for a in _ADAPTERS}


def all_adapters() -> list[ToolAdapter]:
    return list(_ADAPTERS)


def get(name: str) -> ToolAdapter | None:
    return _BY_NAME.get(name.lower())


def by_category() -> dict[Category, list[ToolAdapter]]:
    grouped: dict[Category, list[ToolAdapter]] = {c: [] for c in Category}
    for adapter in _ADAPTERS:
        grouped[adapter.meta.category].append(adapter)
    return {c: items for c, items in grouped.items() if items}
