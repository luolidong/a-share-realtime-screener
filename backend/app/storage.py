from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

DB_PATH = Path(os.getenv("SCREENER_DB_PATH", "/data/screener.db"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL,
                status TEXT NOT NULL,
                matched_count INTEGER NOT NULL DEFAULT 0,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS active_matches (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entered_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                price REAL,
                pct_change REAL,
                turnover_rate REAL,
                net_inflow_cny REAL,
                net_profit_yoy REAL,
                revenue_yoy REAL
            );

            CREATE TABLE IF NOT EXISTS scan_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL,
                pct_change REAL,
                turnover_rate REAL,
                net_inflow_cny REAL,
                net_profit_yoy REAL,
                revenue_yoy REAL
            );

            CREATE INDEX IF NOT EXISTS idx_scan_events_time ON scan_events(event_at DESC);
            CREATE INDEX IF NOT EXISTS idx_scan_events_code ON scan_events(code, event_at DESC);
            """
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value):
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def record_scan(result: pd.DataFrame) -> dict:
    now = _now_iso()
    rows = {str(row["code"]): {k: _clean(v) for k, v in row.items()} for row in result.to_dict(orient="records")}

    with _connect() as conn:
        existing = {
            row["code"]: dict(row)
            for row in conn.execute("SELECT * FROM active_matches").fetchall()
        }

        entered = sorted(set(rows) - set(existing))
        exited = sorted(set(existing) - set(rows))

        for code, row in rows.items():
            if code in entered:
                conn.execute(
                    """INSERT INTO scan_events
                    (event_at, event_type, code, name, price, pct_change, turnover_rate, net_inflow_cny, net_profit_yoy, revenue_yoy)
                    VALUES (?, 'ENTER', ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        now, code, row["name"], row.get("price"), row.get("pct_change"),
                        row.get("turnover_rate"), row.get("net_inflow_cny"),
                        row.get("net_profit_yoy"), row.get("revenue_yoy"),
                    ),
                )

            entered_at = existing.get(code, {}).get("entered_at", now)
            conn.execute(
                """INSERT INTO active_matches
                (code, name, entered_at, updated_at, price, pct_change, turnover_rate, net_inflow_cny, net_profit_yoy, revenue_yoy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name=excluded.name,
                    updated_at=excluded.updated_at,
                    price=excluded.price,
                    pct_change=excluded.pct_change,
                    turnover_rate=excluded.turnover_rate,
                    net_inflow_cny=excluded.net_inflow_cny,
                    net_profit_yoy=excluded.net_profit_yoy,
                    revenue_yoy=excluded.revenue_yoy""",
                (
                    code, row["name"], entered_at, now, row.get("price"), row.get("pct_change"),
                    row.get("turnover_rate"), row.get("net_inflow_cny"),
                    row.get("net_profit_yoy"), row.get("revenue_yoy"),
                ),
            )

        for code in exited:
            row = existing[code]
            conn.execute(
                """INSERT INTO scan_events
                (event_at, event_type, code, name, price, pct_change, turnover_rate, net_inflow_cny, net_profit_yoy, revenue_yoy)
                VALUES (?, 'EXIT', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now, code, row["name"], row.get("price"), row.get("pct_change"),
                    row.get("turnover_rate"), row.get("net_inflow_cny"),
                    row.get("net_profit_yoy"), row.get("revenue_yoy"),
                ),
            )
            conn.execute("DELETE FROM active_matches WHERE code = ?", (code,))

        conn.execute(
            "INSERT INTO scan_runs(scanned_at, status, matched_count) VALUES (?, 'ok', ?)",
            (now, len(rows)),
        )

    return {"entered": entered, "exited": exited, "matched_count": len(rows), "scanned_at": now}


def record_scan_error(error: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO scan_runs(scanned_at, status, matched_count, error) VALUES (?, 'error', 0, ?)",
            (_now_iso(), error[:1000]),
        )


def get_active_matches(limit: int = 500) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM active_matches ORDER BY net_inflow_cny DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_events(limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM scan_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_last_scan() -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None
