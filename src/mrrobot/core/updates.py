"""Version and update checks for the tools.

On startup, mrrobot can warn which built-in tools have a newer upstream
version. The network check is best-effort with a short timeout: it must
never block startup.
"""

from __future__ import annotations

import re
import subprocess

import httpx
from packaging.version import InvalidVersion, Version

from .models import ToolMeta, ToolStatus
from .runner import which

_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


def _parse_version(text: str) -> str | None:
    match = _VERSION_RE.search(text or "")
    return match.group(1) if match else None


def is_newer(candidate: str, current: str) -> bool:
    """Is 'candidate' a newer version than 'current'?"""
    try:
        return Version(candidate) > Version(current)
    except InvalidVersion:
        return candidate.strip() != current.strip()


def installed_version(meta: ToolMeta) -> str | None:
    if not meta.version_cmd:
        return None
    binary = which(meta.version_cmd[0])
    if binary is None:
        return None
    try:
        proc = subprocess.run(
            [binary, *meta.version_cmd[1:]],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return _parse_version(proc.stdout + proc.stderr)


def latest_github_release(repo: str, *, client: httpx.Client | None = None) -> str | None:
    """Latest published GitHub release for 'owner/name'. None on failure."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    owns_client = client is None
    client = client or httpx.Client(timeout=6.0)
    try:
        resp = client.get(url, headers={"Accept": "application/vnd.github+json"})
        if resp.status_code != 200:
            return None
        tag = resp.json().get("tag_name") or ""
        return _parse_version(tag) or (tag or None)
    except (httpx.HTTPError, ValueError):
        return None
    finally:
        if owns_client:
            client.close()


def check_tool(meta: ToolMeta, *, online: bool, client: httpx.Client | None = None) -> ToolStatus:
    """Build a tool's status (installed, version, update)."""
    if meta.builtin:
        # Implemented in Python inside mrrobot: always available, its
        # "version" is the package's own version.
        return ToolStatus(meta=meta, installed=True, path="(built into mrrobot)")

    path = which(meta.binary)
    status = ToolStatus(meta=meta, installed=path is not None, path=path)
    if not status.installed:
        return status
    status.installed_version = installed_version(meta)
    if online and meta.repo:
        status.latest_version = latest_github_release(meta.repo, client=client)
    return status
