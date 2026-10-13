"""WHOIS: registrant, registration/expiry dates and DNS servers.

Built in, no external binary: speaks the WHOIS protocol (RFC 3912) over a
raw socket directly against the TLD's authoritative registry, following
the referral IANA gives. PASSIVE: queries a public registry service, not
the target.
"""

from __future__ import annotations

import re
import socket
import time

from ...core.models import Category, Mode, RunResult, TargetKind, ToolMeta
from ..base import ToolAdapter, make_result

_IANA_WHOIS = "whois.iana.org"
_REFER_RE = re.compile(r"^refer:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
_WHOIS_SERVER_RE = re.compile(r"^whois:\s*(\S+)", re.IGNORECASE | re.MULTILINE)


def _query(server: str, query: str, *, timeout: float) -> str:
    with socket.create_connection((server, 43), timeout=timeout) as sock:
        sock.sendall((query + "\r\n").encode("utf-8", errors="ignore"))
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


class Whois(ToolAdapter):
    meta = ToolMeta(
        name="whois",
        category=Category.OSINT,
        mode=Mode.PASSIVE,
        target_kind=TargetKind.DOMAIN,
        summary="Registrant, registration/expiry dates and authoritative DNS for a domain.",
        builtin=True,
    )

    def execute(self, target: str, *, timeout: int = 300, **options: object) -> RunResult:
        start = time.time()
        domain = target.strip().lower()
        try:
            # 1) Ask IANA which registry handles this TLD.
            referral = _query(_IANA_WHOIS, domain, timeout=min(timeout, 10))
            match = _WHOIS_SERVER_RE.search(referral) or _REFER_RE.search(referral)
            server = match.group(1) if match else _IANA_WHOIS
            # 2) Ask the authoritative registry directly.
            raw = _query(server, domain, timeout=min(timeout, 10))
        except OSError as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"Couldn't complete the WHOIS query: {exc}",
                started_at=start, command=[f"whois {domain}"],
            )

        # Keep only lines with real content, filtering out legal boilerplate.
        useful = [
            ln.rstrip() for ln in raw.splitlines()
            if ln.strip() and not ln.strip().startswith(("%", "#", ">>>"))
        ]
        stdout = "\n".join(useful) if useful else raw.strip()
        return make_result(
            self.meta, target, returncode=0, stdout=stdout, stderr="",
            started_at=start, command=[f"whois {domain} @ {server}"],
        )
