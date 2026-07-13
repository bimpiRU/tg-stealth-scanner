"""SQLite persistence for OSINT targets, findings and scans.

Uses the stdlib sqlite3 module with context managers. The schema is intentionally
small: one target can have many findings and many scans.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from config import DB_PATH
from utils.logger import logger


@contextmanager
def _connect():
    """Yield a connection with row factory set to sqlite3.Row."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_targets_value_type
                ON targets(value, type);

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_text TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_findings_target
                ON findings(target_id);
            CREATE INDEX IF NOT EXISTS idx_findings_category
                ON findings(category);

            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER,
                tool TEXT NOT NULL,
                status TEXT NOT NULL,
                output_path TEXT,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at TEXT,
                FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_scans_target
                ON scans(target_id);
            """
        )
        conn.commit()
    logger.info("Database initialized at %s", DB_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_target(value: str, type_: str) -> int:
    """Insert a target and return its id."""
    value = value.strip().lower()
    type_ = type_.strip().lower()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO targets (value, type, created_at) VALUES (?, ?, ?)",
            (value, type_, _now()),
        )
        conn.commit()
        return cursor.lastrowid


def get_or_create_target(value: str, type_: str) -> int:
    """Return existing target id or create a new one."""
    value = value.strip().lower()
    type_ = type_.strip().lower()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM targets WHERE value = ? AND type = ?",
            (value, type_),
        ).fetchone()
        if row:
            return row["id"]
        cursor = conn.execute(
            "INSERT INTO targets (value, type, created_at) VALUES (?, ?, ?)",
            (value, type_, _now()),
        )
        conn.commit()
        return cursor.lastrowid


def add_finding(
    target_id: int,
    category: str,
    value: str,
    source: str,
    raw_text: Optional[str] = None,
) -> int:
    """Insert a finding and return its id."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO findings (target_id, category, value, source, raw_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (target_id, category.strip().lower(), value.strip(), source, raw_text, _now()),
        )
        conn.commit()
        return cursor.lastrowid


def get_findings(
    target_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 1000,
) -> list[dict]:
    """Return findings as plain dicts, optionally filtered."""
    query = "SELECT * FROM findings WHERE 1=1"
    params: list = []
    if target_id is not None:
        query += " AND target_id = ?"
        params.append(target_id)
    if category is not None:
        query += " AND category = ?"
        params.append(category.strip().lower())
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def add_scan(target_id: Optional[int], tool: str, status: str = "started") -> int:
    """Insert a scan record and return its id."""
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scans (target_id, tool, status, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (target_id, tool, status, _now()),
        )
        conn.commit()
        return cursor.lastrowid


def update_scan_status(
    scan_id: int,
    status: str,
    output_path: Optional[str] = None,
) -> None:
    """Update scan status and optional output path."""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE scans
            SET status = ?, output_path = ?, finished_at = ?
            WHERE id = ?
            """,
            (status, output_path, _now(), scan_id),
        )
        conn.commit()


def get_scan_history(target_id: Optional[int] = None, limit: int = 100) -> list[dict]:
    """Return scan history as plain dicts, newest first."""
    query = "SELECT * FROM scans WHERE 1=1"
    params: list = []
    if target_id is not None:
        query += " AND target_id = ?"
        params.append(target_id)
    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


# --- retention / cleanup ---

_MAX_FINDINGS = int(os.getenv("MAX_DB_FINDINGS", "5000"))
_MAX_SCANS = int(os.getenv("MAX_DB_SCANS", "1000"))
_DB_RETENTION_DAYS = int(os.getenv("DB_RETENTION_DAYS", "30"))


def prune_db() -> dict[str, int]:
    """Delete old findings/scans to keep the SQLite DB bounded.

    Keeps the newest MAX_DB_FINDINGS findings and MAX_DB_SCANS scans, plus
    anything created within DB_RETENTION_DAYS days.
    """
    deleted = {"findings": 0, "scans": 0}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_DB_RETENTION_DAYS)).isoformat()

    with _connect() as conn:
        # Delete by age
        deleted["findings"] += conn.execute(
            "DELETE FROM findings WHERE created_at < ?", (cutoff,)
        ).rowcount
        deleted["scans"] += conn.execute(
            "DELETE FROM scans WHERE started_at < ?", (cutoff,)
        ).rowcount

        # Delete excess rows, newest kept
        cur = conn.execute(
            """
            DELETE FROM findings
            WHERE id NOT IN (
                SELECT id FROM findings ORDER BY created_at DESC LIMIT ?
            )
            """,
            (_MAX_FINDINGS,),
        )
        deleted["findings"] += cur.rowcount

        cur = conn.execute(
            """
            DELETE FROM scans
            WHERE id NOT IN (
                SELECT id FROM scans ORDER BY started_at DESC LIMIT ?
            )
            """,
            (_MAX_SCANS,),
        )
        deleted["scans"] += cur.rowcount

        conn.commit()

    logger.info("DB prune finished: findings=%s scans=%s", deleted["findings"], deleted["scans"])
    return deleted
