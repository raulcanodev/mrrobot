"""crt.sh: descubrimiento de subdominios vía transparencia de certificados.

Integrado (sin binario externo): consulta la API pública de crt.sh, que
indexa los registros de Certificate Transparency. PASIVO: no toca el
objetivo, solo interroga una base de datos de terceros sobre certificados
ya emitidos públicamente. Complementa a subfinder con una fuente distinta.
"""

from __future__ import annotations

import time

import httpx

from ...core.models import Category, Mode, RunResult, TargetKind, ToolMeta
from ..base import ToolAdapter, make_result


class CrtSh(ToolAdapter):
    meta = ToolMeta(
        name="crtsh",
        category=Category.WEB,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.DOMAIN,
        summary="Subdominios a partir de certificados TLS emitidos (Certificate Transparency).",
        builtin=True,
    )

    def execute(self, target: str, *, timeout: int = 300, **options: object) -> RunResult:
        start = time.time()
        url = "https://crt.sh/"
        params = {"q": f"%.{target}", "output": "json"}
        try:
            resp = httpx.get(url, params=params, timeout=min(timeout, 30))
            resp.raise_for_status()
            rows = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"No se pudo consultar crt.sh: {exc}", started_at=start,
                command=[url, f"q={params['q']}"],
            )

        names: set[str] = set()
        for row in rows:
            for name in str(row.get("name_value", "")).splitlines():
                name = name.strip().lstrip("*.")
                if name:
                    names.add(name)

        stdout = "\n".join(sorted(names)) if names else "(sin resultados en crt.sh)"
        return make_result(
            self.meta, target, returncode=0, stdout=stdout, stderr="",
            started_at=start, command=[url, f"q={params['q']}"],
        )
