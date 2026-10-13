"""Shodan InternetDB: known ports, services, CPEs and CVEs for an IP.

Built in, no API key. PASSIVE: queries Shodan's public database about that
IP (a snapshot of Shodan's previous scans), without sending any packet to
the target. The fastest way to get a snapshot of a host's exposure
without scanning it yourself.
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
        summary="Known ports, services and CVEs for an IP, per Shodan (no API key).",
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
                stderr=f"Couldn't query InternetDB: {exc}", started_at=start,
                command=[url],
            )

        if resp.status_code == 404:
            return make_result(
                self.meta, target, returncode=0,
                stdout="Shodan has no data on record for this IP.",
                stderr="", started_at=start, command=[url],
            )
        try:
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"Unexpected response from InternetDB: {exc}", started_at=start,
                command=[url],
            )

        lines = [
            f"IP:        {data.get('ip', target)}",
            f"Hostnames: {', '.join(data.get('hostnames', [])) or '—'}",
            f"Ports:     {', '.join(str(p) for p in data.get('ports', [])) or '—'}",
            f"CPEs:      {', '.join(data.get('cpes', [])) or '—'}",
        ]
        vulns = data.get("vulns", [])
        if vulns:
            lines.append(f"CVEs:      {', '.join(vulns)}")
        return make_result(
            self.meta, target, returncode=0, stdout="\n".join(lines),
            stderr="", started_at=start, command=[url],
        )
