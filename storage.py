"""SQLite persistence for counting sessions and gate crossings."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

DB_PATH = Path("runs/animal_tracker.sqlite3")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize() -> None:
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT
            );
            CREATE TABLE IF NOT EXISTS crossings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                occurred_at TEXT NOT NULL,
                track_id TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('out', 'in'))
            );
        """)


def start_session() -> int:
    initialize()
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO sessions (started_at) VALUES (?)",
            (datetime.now().astimezone().isoformat(timespec="seconds"),),
        )
        return int(cursor.lastrowid)


def record_crossing(session_id: int, track_id: str, direction: str) -> str:
    occurred_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with connect() as db:
        db.execute(
            "INSERT INTO crossings (session_id, occurred_at, track_id, direction) VALUES (?, ?, ?, ?)",
            (session_id, occurred_at, track_id, direction),
        )
    return occurred_at


def end_session(session_id: int) -> None:
    with connect() as db:
        db.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
            (datetime.now().astimezone().isoformat(timespec="seconds"), session_id),
        )


def dashboard_state() -> dict:
    initialize()
    with connect() as db:
        session = db.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if session is None:
            return {"session": None, "counts": {"out": 0, "in": 0, "still_out": 0}, "events": []}

        session_id = session["id"]
        totals = db.execute(
            "SELECT direction, COUNT(*) AS total FROM crossings WHERE session_id = ? GROUP BY direction",
            (session_id,),
        ).fetchall()
        counts = {row["direction"]: row["total"] for row in totals}
        went_out = counts.get("out", 0)
        came_back = counts.get("in", 0)
        events = db.execute(
            "SELECT occurred_at, track_id, direction FROM crossings "
            "WHERE session_id = ? ORDER BY id DESC LIMIT 100",
            (session_id,),
        ).fetchall()
        return {
            "session": dict(session),
            "counts": {"out": went_out, "in": came_back, "still_out": max(0, went_out - came_back)},
            "events": [dict(row) for row in events],
        }
