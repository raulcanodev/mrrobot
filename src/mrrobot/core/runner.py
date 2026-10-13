"""Execution of external tools.

We orchestrate existing processes instead of reimplementing their logic.
The runner is synchronous and simple, but kept isolated so async or
concurrent execution can be added later without touching the rest of core.
"""

from __future__ import annotations

import shutil
import subprocess
import time

from .models import RunResult, ToolMeta


class ToolNotInstalled(RuntimeError):
    pass


class NotAuthorized(PermissionError):
    """An ACTIVE action was attempted against a target outside of scope."""


def which(binary: str) -> str | None:
    return shutil.which(binary)


def run_tool(
    meta: ToolMeta,
    args: list[str],
    target: str,
    *,
    timeout: int = 300,
) -> RunResult:
    """Launch the tool and return a normalized result.

    The authorization check happens one layer up (in the adapter), so the
    runner only ever has to worry about execution.
    """
    binary = which(meta.binary)
    if binary is None:
        raise ToolNotInstalled(meta.binary)

    command = [binary, *args]
    start = time.time()
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\n[mrrobot] timed out after {timeout}s"
        code = 124

    return RunResult(
        tool=meta.name,
        target=target,
        mode=meta.mode,
        command=command,
        returncode=code,
        stdout=stdout if isinstance(stdout, str) else "",
        stderr=stderr if isinstance(stderr, str) else "",
        started_at=start,
        duration_s=round(time.time() - start, 2),
    )
