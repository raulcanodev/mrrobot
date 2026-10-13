"""Wayback Machine: historical URLs indexed for a domain.

Built in, no external binary. Equivalent to the classic `waybackurls`, but
hitting archive.org's CDX API directly. PASSIVE: queries the Internet
Archive, not the target. Useful for finding forgotten routes, parameters,
endpoints or subdomains that are still indexed even if no longer linked
from the current web.
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
        summary="Historical URLs for a domain indexed by the Internet Archive.",
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
            # The CDX API is notoriously slow on heavily-indexed domains;
            # a moderate default limit avoids endless waits.
            "limit": str(limit) if limit else "1000",
        }
        try:
            resp = httpx.get(_CDX_URL, params=params, timeout=min(timeout, 45))
            resp.raise_for_status()
            rows = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"Couldn't query the Wayback Machine: {exc}",
                started_at=start, command=[_CDX_URL, f"url={params['url']}"],
            )

        # The first row is the header ("original"); the rest are URLs.
        urls = sorted({row[0] for row in rows[1:] if row})
        stdout = "\n".join(urls) if urls else "(no historical URLs indexed)"
        return make_result(
            self.meta, target, returncode=0, stdout=stdout, stderr="",
            started_at=start, command=[_CDX_URL, f"url={params['url']}"],
        )
