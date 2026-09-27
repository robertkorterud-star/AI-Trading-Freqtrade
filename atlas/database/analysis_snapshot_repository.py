"""
ATLAS Analysis Snapshot Repository

Database access for persistent analysis snapshots.
"""

import json
from datetime import datetime

from atlas.database.connection import Database
from atlas.models.analysis_snapshot import AnalysisSnapshot


class AnalysisSnapshotRepository:
    """Stores and retrieves analysis snapshots."""

    def __init__(self, database: Database):
        self.database = database

    def save(self, snapshot: AnalysisSnapshot):
        """Insert a new analysis snapshot."""

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO analysis_snapshots (
                    symbol,
                    timestamp,
                    provider,
                    model,
                    results,
                    decision,
                    intelligence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.symbol,
                    snapshot.timestamp.isoformat(),
                    snapshot.provider,
                    snapshot.model,
                    json.dumps(
                        snapshot.results,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        snapshot.decision,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        snapshot.intelligence,
                        ensure_ascii=False,
                    ),
                ),
            )

            connection.commit()

            snapshot.database_id = cursor.lastrowid

            if snapshot.decision_ref is not None:
                snapshot.decision_ref.analysis_snapshot_id = cursor.lastrowid

            return cursor.lastrowid

    def get_by_id(self, snapshot_id: int):
        """Return one canonical snapshot by database ID."""

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM analysis_snapshots
                WHERE id = ?
                LIMIT 1
                """,
                (snapshot_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_snapshot(row)

    def get_latest(self, symbol: str):
        """Return the newest snapshot for a symbol."""

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM analysis_snapshots
                WHERE symbol = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_snapshot(row)

    def get_latest_valid(self, symbol: str):
        """Return the newest complete snapshot for a symbol."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM analysis_snapshots
                WHERE symbol = ?
                ORDER BY timestamp DESC, id DESC
                """,
                (symbol,),
            ).fetchall()

        for row in rows:
            snapshot = self._row_to_snapshot(row)

            if self._is_valid_snapshot(snapshot):
                return snapshot

        return None

    @staticmethod
    def _is_valid_snapshot(snapshot):
        """Return True when a snapshot is complete for the dashboard."""

        if not snapshot.results:
            return False

        decision = snapshot.decision
        intelligence = snapshot.intelligence

        required_decision = {
            "action",
            "confidence",
            "evidence",
        }

        required_intelligence = {
            "action",
            "buy_count",
            "hold_count",
            "sell_count",
            "agreement",
        }

        if not required_decision.issubset(
            decision.keys()
        ):
            return False

        if not required_intelligence.issubset(
            intelligence.keys()
        ):
            return False

        return True

    def get_all(self, symbol: str | None = None):
        """Return snapshots from newest to oldest."""

        with self.database.connect() as connection:

            if symbol is None:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM analysis_snapshots
                    ORDER BY timestamp DESC, id DESC
                    """
                ).fetchall()

            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM analysis_snapshots
                    WHERE symbol = ?
                    ORDER BY timestamp DESC, id DESC
                    """,
                    (symbol,),
                ).fetchall()

        return [
            self._row_to_snapshot(row)
            for row in rows
        ]

    def count(self):
        """Return number of stored snapshots."""

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM analysis_snapshots
                """
            ).fetchone()

        return int(row["count"])

    def clear(self):
        """Delete all analysis snapshots."""

        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM analysis_snapshots"
            )
            connection.commit()

    @staticmethod
    def _row_to_snapshot(row):
        """Convert a database row into AnalysisSnapshot."""

        return AnalysisSnapshot(
            database_id=int(row["id"]),
            symbol=row["symbol"],
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            provider=row["provider"],
            model=row["model"],
            results=json.loads(row["results"]),
            decision=json.loads(row["decision"]),
            intelligence=json.loads(
                row["intelligence"]
            ),
        )
