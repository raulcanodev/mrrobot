"""Execution of external tools.

We orchestrate existing processes instead of reimplementing their logic.
The runner is synchronous and simple, but kept isolated so async or
concurrent execution can be added later without touching the rest of core.

Each tool runs in its own process group (POSIX) so that on Ctrl+C we can
reliably kill it and any children it spawned ourselves, deterministically,
instead of depending on whether the terminal's job control happens to
forward the signal to it.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import time

from .models import RunResult, ToolMeta


class ToolNotInstalled(RuntimeError):
    pass


class NotAuthorized(PermissionError):
    """An ACTIVE action was attempted against a target outside of scope."""


def which(binary: str) -> str | None:
    return shutil.which(binary)


def _kill(proc: subprocess.Popen) -> None:
    """Terminate the process (and its whole group on POSIX), then make sure."""
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            else:
                proc.kill()
        except (ProcessLookupError, PermissionError):
            pass
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=2)


def run_tool(
    meta: ToolMeta,
    args: list[str],
    target: str,
    *,
    timeout: int = 300,
) -> RunResult:
    """Launch the tool and return a normalized result.

    The authorization check happens one layer up (in the adapter), so the
    runner only ever has to worry about execution. Raises KeyboardInterrupt
    (after killing the process cleanly) if the user hits Ctrl+C mid-run.
    """
    binary = which(meta.binary)
    if binary is None:
        raise ToolNotInstalled(meta.binary)

    command = [binary, *args]
    start = time.time()
    popen_kwargs: dict[str, object] = {}
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **popen_kwargs,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        _kill(proc)
        stdout, stderr = proc.communicate()
        stderr = (stderr or "") + f"\n[mrrobot] timed out after {timeout}s"
        code = 124
    except KeyboardInterrupt:
        _kill(proc)
        raise

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
