"""Reports: aggregate the results of several tools against one target.

Kept separate from the CLI so the reporting engine (what ran, in what
order, with what result) is reusable by any future interface. The CLI only
handles the interactive part (asking, showing, saving).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR, ensure_dirs
from .models import Mode, RunResult

REPORTS_DIR = DATA_DIR / "reports"

# A section's status when there was no RunResult (blocked or not installed).
Status = str  # "ok" | "fail" | "blocked" | "missing"


@dataclass
class Section:
    """One tool's result within a report."""

    tool: str
    mode: Mode
    status: Status
    detail: str = ""
    result: RunResult | None = None


@dataclass
class Report:
    """A full report: one target and what each tool found about it."""

    target: str
    kind: str
    sections: list[Section] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_text(self) -> str:
        """Full plain-text representation, meant for a .txt file."""
        when = datetime.fromtimestamp(self.generated_at).strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 72,
            "  mrrobot REPORT",
            "=" * 72,
            f"Target:    {self.target}  ({self.kind})",
            f"Generated: {when}",
            f"Sections:  {len(self.sections)}",
            "",
        ]
        for sec in self.sections:
            lines.append("-" * 72)
            lines.append(f"[{sec.tool}]  mode={sec.mode.value}  status={sec.status}")
            if sec.detail:
                lines.append(sec.detail)
            if sec.result is not None:
                r = sec.result
                lines.append(f"command:  {' '.join(r.command)}")
                lines.append(f"duration: {r.duration_s}s   exit code: {r.returncode}")
                lines.append("")
                lines.append(r.stdout.rstrip() or "(no output)")
                if r.stderr.strip():
                    lines.append("")
                    lines.append("stderr:")
                    lines.append(r.stderr.rstrip())
            lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)


def default_report_path(target: str) -> Path:
    ensure_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in target.strip()) or "target"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return REPORTS_DIR / f"{safe}-{stamp}.txt"


def save_report(report: Report, path: Path | None = None) -> Path:
    path = path or default_report_path(report.target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_text(), encoding="utf-8")
    return path
