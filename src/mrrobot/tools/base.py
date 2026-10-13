"""Base adapter for tools, whether external or built-in.

Every tool we integrate subclasses ToolAdapter. There are two ways to
implement one:

  1. External (most of them): override `build_args()` to translate a
     high-level request into the binary's arguments. `execute()` already
     knows how to launch the process with those arguments.
  2. Built-in ("builtin", no external binary, e.g. a public API call):
     override `execute()` directly and build its own `RunResult` with
     `make_result()`.

The shared logic (scope authorization, timing, normalization) lives here,
so adding a new tool is just a few lines.
"""

from __future__ import annotations

import time
from abc import ABC

from ..core.config import Scope
from ..core.models import Mode, RunResult, ToolMeta
from ..core.runner import NotAuthorized, run_tool


def make_result(
    meta: ToolMeta,
    target: str,
    *,
    returncode: int,
    stdout: str,
    stderr: str,
    started_at: float,
    command: list[str] | None = None,
) -> RunResult:
    """Build a uniform RunResult for built-in tools."""
    return RunResult(
        tool=meta.name,
        target=target,
        mode=meta.mode,
        command=command or [f"(built-in) {meta.name}"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        started_at=started_at,
        duration_s=round(time.time() - started_at, 2),
    )


class ToolAdapter(ABC):
    meta: ToolMeta

    def build_args(self, target: str, **options: object) -> list[str]:
        """Translate the request into the binary's arguments. Only needed by
        external tools; built-in ones override execute() instead."""
        raise NotImplementedError(
            f"{type(self).__name__} doesn't implement build_args(); "
            "if it's a built-in tool, override execute() instead."
        )

    def execute(self, target: str, *, timeout: int = 300, **options: object) -> RunResult:
        """Run the tool and return the result. By default launches the
        external binary via build_args(); built-in tools override this."""
        args = self.build_args(target, **options)
        return run_tool(self.meta, args, target, timeout=timeout)

    def run(
        self,
        target: str,
        *,
        scope: Scope,
        timeout: int = 300,
        **options: object,
    ) -> RunResult:
        # Authorization gate: ACTIVE actions only against in-scope targets.
        if self.meta.mode is Mode.ACTIVE and not scope.allows(target):
            raise NotAuthorized(
                f"'{target}' is not in your authorized scope. "
                f"'{self.meta.name}' sends traffic to the target "
                f"(ACTIVE mode) and requires explicit permission. "
                f"Run 'mrrobot scope init' and declare the target."
            )
        return self.execute(target, timeout=timeout, **options)
