"""Wayback Machine: URLs históricas indexadas de un dominio.

Integrado, sin binario externo. Equivalente al clásico `waybackurls`, pero
contra la API CDX de archive.org directamente. PASIVO: consulta el archivo
de Internet Archive, no el objetivo. Útil para encontrar rutas, parámetros,
endpoints o subdominios olvidados que siguen indexados aunque ya no estén
enlazados desde la web actual.
"""

from __future__ import annotations

import time

import httpx

from ...core.models import Category, Mode, RunResult, TargetKind, ToolMeta
from ..base import ToolAdapter, make_result

_CDX_URL = "https://web.archive.org/cdx/search/cdx"


class Wayback(ToolAdapter):
    meta = ToolMeta(
        name="wayback",
        category=Category.WEB,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.DOMAIN,
        summary="URLs históricas de un dominio indexadas por Internet Archive.",
        builtin=True,
    )

    def execute(self, target: str, *, timeout: int = 300, **options: object) -> RunResult:
        start = time.time()
        limit = options.get("limit")
        params = {
            "url": f"*.{target}/*",
            "output": "json",
            "fl": "original",
            "collapse": "urlkey",
            # La API CDX es notoriamente lenta en dominios muy indexados;
            # un límite moderado por defecto evita esperas eternas.
            "limit": str(limit) if limit else "1000",
        }
        try:
            resp = httpx.get(_CDX_URL, params=params, timeout=min(timeout, 45))
            resp.raise_for_status()
            rows = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"No se pudo consultar Wayback Machine: {exc}",
                started_at=start, command=[_CDX_URL, f"url={params['url']}"],
            )

        # La primera fila es la cabecera ("original"); el resto son URLs.
        urls = sorted({row[0] for row in rows[1:] if row})
        stdout = "\n".join(urls) if urls else "(sin URLs históricas indexadas)"
        return make_result(
            self.meta, target, returncode=0, stdout=stdout, stderr="",
            started_at=start, command=[_CDX_URL, f"url={params['url']}"],
        )
