"""SQLite storage for trips. Times are stored as UTC ISO strings of fixed length."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.models import Trip

SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id         TEXT PRIMARY KEY,
    start_utc  TEXT NOT NULL,
    end_utc    TEXT NOT NULL,
    amount     INTEGER NOT NULL,
    payment    TEXT NOT NULL,
    commission INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS trips_start_utc ON trips(start_utc);
"""

COLUMNS = "id, start_utc, end_utc, amount, payment, commission"


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path)


def init_db(path: Path) -> None:
    with closing(connect(path)) as conn:
        conn.executescript(SCHEMA)


def to_utc_text(moment: datetime) -> str:
    """Same length for every moment, so text order equals time order."""
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _from_row(row: tuple) -> Trip:
    id, start_utc, end_utc, amount, payment, commission = row
    return Trip(
        id=id,
        start=datetime.fromisoformat(start_utc),
        end=datetime.fromisoformat(end_utc),
        amount=amount,
        payment=payment,
        commission=commission,
    )


def save_trip(conn: sqlite3.Connection, trip: Trip) -> tuple[Trip, bool]:
    """Insert the trip; if its id already exists, return the stored one. Returns (trip, created)."""
    row = (
        trip.id,
        to_utc_text(trip.start),
        to_utc_text(trip.end),
        trip.amount,
        trip.payment,
        trip.commission,
    )
    try:
        with conn:
            conn.execute(f"INSERT INTO trips ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)", row)
    except sqlite3.IntegrityError:
        stored = conn.execute(f"SELECT {COLUMNS} FROM trips WHERE id = ?", (trip.id,)).fetchone()
        return _from_row(stored), False
    return trip, True


def trips_between(conn: sqlite3.Connection, start: datetime, end: datetime) -> list[Trip]:
    """Trips whose start is in [start, end), ordered by start, then id."""
    rows = conn.execute(
        f"SELECT {COLUMNS} FROM trips WHERE start_utc >= ? AND start_utc < ? ORDER BY start_utc, id",
        (to_utc_text(start), to_utc_text(end)),
    ).fetchall()
    return [_from_row(row) for row in rows]
