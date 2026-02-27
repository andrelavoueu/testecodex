from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import TripRecord


def connect_db(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT NOT NULL,
            traveler TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            purchase_date TEXT NOT NULL,
            purchase_lead_days INTEGER NOT NULL,
            destination TEXT NOT NULL,
            consultant TEXT NOT NULL,
            status TEXT NOT NULL,
            source_email TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def upsert_trip(conn: sqlite3.Connection, record: TripRecord) -> None:
    conn.execute(
        """
        INSERT INTO trips (
            client,
            traveler,
            travel_date,
            purchase_date,
            purchase_lead_days,
            destination,
            consultant,
            status,
            source_email
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_email) DO UPDATE SET
            client=excluded.client,
            traveler=excluded.traveler,
            travel_date=excluded.travel_date,
            purchase_date=excluded.purchase_date,
            purchase_lead_days=excluded.purchase_lead_days,
            destination=excluded.destination,
            consultant=excluded.consultant,
            status=excluded.status
        """,
        (
            record.client,
            record.traveler,
            record.travel_date.isoformat(),
            record.purchase_date.isoformat(),
            record.purchase_lead_days,
            record.destination,
            record.consultant,
            record.status,
            record.source_email,
        ),
    )
    conn.commit()


def list_trips(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT
            client,
            traveler,
            travel_date,
            purchase_date,
            purchase_lead_days,
            destination,
            consultant,
            status,
            source_email
        FROM trips
        ORDER BY travel_date ASC
        """
    ).fetchall()
    return list(rows)
