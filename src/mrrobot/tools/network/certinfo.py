"""certinfo: inspecciona el certificado TLS que presenta un host.

Integrado, sin binario externo (usa el módulo `ssl` de la librería estándar).
Muestra emisor, validez, nombres alternativos (SANs) —útiles para descubrir
subdominios hermanos en el mismo certificado— y el cifrado negociado.

ACTIVO: abre una conexión TCP/TLS real contra el objetivo (equivalente a
visitar el sitio con un navegador), así que requiere scope autorizado.
"""

from __future__ import annotations

import socket
import ssl
import time

from ...core.models import Category, Mode, RunResult, TargetKind, ToolMeta
from ..base import ToolAdapter, make_result


def _split_host_port(target: str) -> tuple[str, int]:
    # "host:port" tiene exactamente un ':'; una IPv6 pelada tendría varios
    # y la dejamos tal cual con el puerto 443 por defecto.
    if target.count(":") == 1:
        host, _, port = target.partition(":")
        return host, int(port)
    return target, 443


class CertInfo(ToolAdapter):
    meta = ToolMeta(
        name="certinfo",
        category=Category.NETWORK,
        mode=Mode.ACTIVE,
        target_kind=TargetKind.HOST,
        summary="Emisor, validez, SANs y cifrado del certificado TLS de un host.",
        builtin=True,
    )

    def execute(self, target: str, *, timeout: int = 300, **options: object) -> RunResult:
        start = time.time()
        host, port = _split_host_port(target)
        connect_timeout = min(timeout, 15)
        lines: list[str] = []
        warnings: list[str] = []

        cert: dict | None = None
        cipher = None
        tls_version = None
        try:
            ctx = ssl.create_default_context()
            with (
                socket.create_connection((host, port), timeout=connect_timeout) as raw,
                ctx.wrap_socket(raw, server_hostname=host) as tls,
            ):
                cert = tls.getpeercert()
                cipher = tls.cipher()
                tls_version = tls.version()
        except ssl.SSLCertVerificationError as exc:
            warnings.append(f"cadena de confianza no verificada: {exc.verify_message}")
            try:
                ctx = ssl._create_unverified_context()
                with (
                    socket.create_connection((host, port), timeout=connect_timeout) as raw,
                    ctx.wrap_socket(raw, server_hostname=host) as tls,
                ):
                    cipher = tls.cipher()
                    tls_version = tls.version()
            except OSError as exc2:
                warnings.append(f"tampoco se pudo negociar TLS sin verificar: {exc2}")
        except (OSError, TimeoutError) as exc:
            return make_result(
                self.meta, target, returncode=1, stdout="",
                stderr=f"No se pudo conectar a {host}:{port}: {exc}",
                started_at=start, command=[f"tls-handshake {host}:{port}"],
            )

        if cert:
            subject = dict(x[0] for x in cert.get("subject", []))
            issuer = dict(x[0] for x in cert.get("issuer", []))
            sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
            lines += [
                f"Sujeto:    {subject.get('commonName', '—')}",
                f"Emisor:    {issuer.get('commonName', '—')}",
                f"Válido:    {cert.get('notBefore', '—')} → {cert.get('notAfter', '—')}",
                f"SANs:      {', '.join(sans) if sans else '—'}",
            ]
        if tls_version or cipher:
            cipher_name = cipher[0] if cipher else "—"
            lines.append(f"TLS:       {tls_version or '—'} ({cipher_name})")
        for w in warnings:
            lines.append(f"⚠ {w}")

        stdout = "\n".join(lines) if lines else "(sin datos de certificado)"
        return make_result(
            self.meta, target, returncode=0, stdout=stdout, stderr="",
            started_at=start, command=[f"tls-handshake {host}:{port}"],
        )
