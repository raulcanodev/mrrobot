"""Informes: agregan los resultados de varias herramientas sobre un objetivo.

Separado de la CLI para que el motor de informes (qué se ejecutó, en qué
orden, con qué resultado) sea reutilizable por cualquier interfaz futura.
La CLI solo se encarga de la parte interactiva (preguntar, mostrar, guardar).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR, ensure_dirs
from .models import Mode, RunResult

REPORTS_DIR = DATA_DIR / "reports"

# Estado de una sección cuando no hubo RunResult (bloqueada o no instalada).
Status = str  # "ok" | "fail" | "blocked" | "missing"


@dataclass
class Section:
    """Resultado de una herramienta dentro de un informe."""

    tool: str
    mode: Mode
    status: Status
    detail: str = ""
    result: RunResult | None = None


@dataclass
class Report:
    """Un informe completo: un objetivo y lo que cada herramienta encontró."""

    target: str
    kind: str
    sections: list[Section] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_text(self) -> str:
        """Representación completa en texto plano, pensada para un .txt."""
        when = datetime.fromtimestamp(self.generated_at).strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 72,
            "  INFORME mrrobot",
            "=" * 72,
            f"Objetivo:  {self.target}  ({self.kind})",
            f"Generado:  {when}",
            f"Secciones: {len(self.sections)}",
            "",
        ]
        for sec in self.sections:
            lines.append("-" * 72)
            lines.append(f"[{sec.tool}]  modo={sec.mode.value}  estado={sec.status}")
            if sec.detail:
                lines.append(sec.detail)
            if sec.result is not None:
                r = sec.result
                lines.append(f"comando:  {' '.join(r.command)}")
                lines.append(f"duración: {r.duration_s}s   código de salida: {r.returncode}")
                lines.append("")
                lines.append(r.stdout.rstrip() or "(sin salida)")
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
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in target.strip()) or "objetivo"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return REPORTS_DIR / f"{safe}-{stamp}.txt"


def save_report(report: Report, path: Path | None = None) -> Path:
    path = path or default_report_path(report.target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_text(), encoding="utf-8")
    return path
