"""crt.sh: subdomain discovery via certificate transparency.

Built in (no external binary): queries crt.sh's public API, which indexes
Certificate Transparency logs. PASSIVE: never touches the target, only
queries a third-party database about certificates already issued
publicly. Complements subfinder with a different source.
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
        summary="Subdomains from issued TLS certificates (Certificate Transparency).",
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
                stderr=f"Couldn't query crt.sh: {exc}", started_at=start,
                command=[url, f"q={params['q']}"],
            )

        names: set[str] = set()
        for row in rows:
            for name in str(row.get("name_value", "")).splitlines():
                name = name.strip().lstrip("*.")
                if name:
                    names.add(name)

        stdout = "\n".join(sorted(names)) if names else "(no results on crt.sh)"
        return make_result(
            self.meta, target, returncode=0, stdout=stdout, stderr="",
            started_at=start, command=[url, f"q={params['q']}"],
        )
