"""Almacenamiento de resultados en SQLite.

Guardar cada ejecución permite tener historial, búsquedas y, más adelante,
relacionar hallazgos. Usamos solo la librería estándar para no añadir peso.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import DATA_DIR, ensure_dirs
from .models import RunResult

DB_PATH = DATA_DIR / "mrrobot.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tool        TEXT NOT NULL,
    target      TEXT NOT NULL,
    mode        TEXT NOT NULL,
    returncode  INTEGER NOT NULL,
    command     TEXT NOT NULL,
    stdout      TEXT,
    stderr      TEXT,
    started_at  REAL NOT NULL,
    duration_s  REAL NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def save_run(result: RunResult) -> int:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO runs
                (tool, target, mode, returncode, command, stdout, stderr,
                 started_at, duration_s)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.tool,
                result.target,
                result.mode.value,
                result.returncode,
                json.dumps(result.command),
                result.stdout,
                result.stderr,
                result.started_at,
                result.duration_s,
            ),
        )
        return int(cur.lastrowid or 0)


def recent_runs(limit: int = 20) -> list[sqlite3.Row]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT id, tool, target, mode, returncode, started_at, duration_s "
            "FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()


def db_location() -> Path:
    return DB_PATH
