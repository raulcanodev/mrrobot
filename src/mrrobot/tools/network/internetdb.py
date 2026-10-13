"""Shodan InternetDB: puertos, servicios, CPEs y CVEs conocidos de una IP.

Integrado, sin clave de API. PASIVO: consulta la base de datos pública de
Shodan sobre esa IP (snapshot de escaneos previos de Shodan), sin enviar
ningún paquete al objetivo. Es la forma más rápida de tener una foto de
exposición de un host sin escanearlo tú mismo.
"""

from __future__ import annotations

import time

import httpx

from ...core.models import Category, Mode, RunResult, TargetKind, ToolMeta
from ..base import ToolAdapter, make_result


class InternetDB(ToolAdapter):
    meta = ToolMeta(
        name="internetdb",
        category=Category.NETWORK,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.IP,
        summary="Puertos, servicios y CVEs conocidos de una IP según Shodan (sin API key).",
        builtin=True,
    )

    def execute(self, target: str, *, timeout: int = 300, **options: object) -> RunResult:
        start = time.time()
        url = f"https://internetdb.shodan.io/{target}"
        try:
            resp = httpx.get(url, timeout=min(timeout, 20))
        except httpx.HTTPError as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"No se pudo consultar InternetDB: {exc}", started_at=start,
                command=[url],
            )

        if resp.status_code == 404:
            return make_result(
                self.meta, target, returncode=0,
                stdout="Shodan no tiene datos registrados para esta IP.",
                stderr="", started_at=start, command=[url],
            )
        try:
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"Respuesta inesperada de InternetDB: {exc}", started_at=start,
                command=[url],
            )

        lines = [
            f"IP:        {data.get('ip', target)}",
            f"Hostnames: {', '.join(data.get('hostnames', [])) or '—'}",
            f"Puertos:   {', '.join(str(p) for p in data.get('ports', [])) or '—'}",
            f"CPEs:      {', '.join(data.get('cpes', [])) or '—'}",
        ]
        vulns = data.get("vulns", [])
        if vulns:
            lines.append(f"CVEs:      {', '.join(vulns)}")
        return make_result(
            self.meta, target, returncode=0, stdout="\n".join(lines),
            stderr="", started_at=start, command=[url],
        )
