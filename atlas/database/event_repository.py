"""Persistence for lightweight ATLAS state-change events."""

import json
from datetime import datetime, timezone

from atlas.database.connection import Database


class AtlasEventRepository:
    """Store and read small ATLAS events for dashboard live updates.

    The event log is intentionally SQLite-backed so the ATLAS engine and the
    dashboard can communicate even when they run in separate processes.
    """

    def __init__(self, database: Database):
        self.database = database

    def publish(self, event_type: str, payload: dict | None = None) -> int:
        """Persist one state-change event and return its database id."""
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO atlas_events (event_type, payload, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    event_type,
                    json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
            event_id = int(cursor.lastrowid)

            # Keep this transport log bounded. Dashboard consumers only need
            # recent events; canonical trade/snapshot data lives elsewhere.
            connection.execute(
                """
                DELETE FROM atlas_events
                WHERE id < ?
                """,
                (max(0, event_id - 5000),),
            )
            connection.commit()

        return event_id

    def latest_id(self) -> int:
        """Return the newest event id without loading historical events."""
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(id), 0) AS latest_id FROM atlas_events"
            ).fetchone()
        return int(row["latest_id"])

    def after(self, event_id: int = 0, limit: int = 100):
        """Return events newer than ``event_id`` in ascending order."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, event_type, payload, created_at
                FROM atlas_events
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (int(event_id), int(limit)),
            ).fetchall()

        events = []
        for row in rows:
            try:
                payload = json.loads(row["payload"] or "{}")
            except (TypeError, json.JSONDecodeError):
                payload = {}
            events.append(
                {
                    "id": int(row["id"]),
                    "type": row["event_type"],
                    "payload": payload,
                    "created_at": row["created_at"],
                }
            )
        return events
