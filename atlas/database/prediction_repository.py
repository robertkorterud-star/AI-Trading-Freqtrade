"""
ATLAS Prediction Repository

Database access for prediction records.
"""

import json
from datetime import datetime

from atlas.database.connection import Database
from atlas.trading.prediction_record import PredictionRecord


class PredictionRepository:
    """Stores and retrieves prediction records."""

    def __init__(self, database: Database):
        self.database = database

    def save(self, prediction: PredictionRecord):
        """Insert a new prediction."""

        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO predictions (
                    symbol,
                    action,
                    confidence,
                    evidence,
                    price_usd,
                    timestamp,
                    analysts,
                    reason,
                    features,
                    analysis_snapshot_id,
                    evaluated,
                    correct,
                    evaluated_price_usd,
                    price_change_percent,
                    evaluated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prediction.symbol,
                    prediction.action,
                    prediction.confidence,
                    prediction.evidence,
                    prediction.price_usd,
                    prediction.timestamp.isoformat(),
                    json.dumps(
                        prediction.analysts,
                        ensure_ascii=False,
                    ),
                    prediction.reason,
                    json.dumps(
                        prediction.features,
                        ensure_ascii=False,
                    ),
                    prediction.analysis_snapshot_id,
                    int(prediction.evaluated),
                    (
                        int(prediction.correct)
                        if prediction.correct is not None
                        else None
                    ),
                    prediction.evaluated_price_usd,
                    prediction.price_change_percent,
                    (
                        prediction.evaluated_at.isoformat(
                            timespec="seconds"
                        )
                        if prediction.evaluated_at is not None
                        else None
                    ),
                ),
            )

            connection.commit()

            prediction.database_id = cursor.lastrowid

            return cursor.lastrowid

    def update(
        self,
        prediction_id: int,
        prediction,
        connection=None,
    ):
        """Update an existing prediction."""

        if connection is not None:
            self._update(
                connection,
                prediction_id,
                prediction,
            )
            return

        with self.database.connect() as owned_connection:
            self._update(
                owned_connection,
                prediction_id,
                prediction,
            )
            owned_connection.commit()

    @staticmethod
    def _update(connection, prediction_id: int, prediction):
        """Execute an evaluation update using one SQLite connection."""

        connection.execute(
            """
            UPDATE predictions
            SET
                evaluated = ?,
                correct = ?,
                evaluated_price_usd = ?,
                price_change_percent = ?,
                evaluated_at = ?
            WHERE id = ?
            """,
            (
                int(prediction.evaluated),
                (
                    int(prediction.correct)
                    if prediction.correct is not None
                    else None
                ),
                prediction.evaluated_price_usd,
                prediction.price_change_percent,
                (
                    prediction.evaluated_at.isoformat(
                        timespec="seconds"
                    )
                    if prediction.evaluated_at is not None
                    else None
                ),
                prediction_id,
            ),
        )

    def get_all(self):
        """Return all predictions from newest to oldest."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM predictions
                ORDER BY timestamp DESC, id DESC
                """
            ).fetchall()

        return [
            self._row_to_prediction(row)
            for row in rows
        ]

    def get_pending(self):
        """Return predictions that have not been evaluated."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM predictions
                WHERE evaluated = 0
                ORDER BY timestamp ASC, id ASC
                """
            ).fetchall()

        return [
            self._row_to_prediction(row)
            for row in rows
        ]

    def get_evaluated(self):
        """Return evaluated predictions for performance reconciliation."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM predictions
                WHERE evaluated = 1
                ORDER BY timestamp ASC, id ASC
                """
            ).fetchall()

        return [
            self._row_to_prediction(row)
            for row in rows
        ]

    def count(self):
        """Return number of stored predictions."""

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM predictions
                """
            ).fetchone()

        return int(row["count"])

    def clear(self):
        """Delete all predictions."""

        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM predictions"
            )
            connection.commit()

    @staticmethod
    def _row_to_prediction(row):
        """Convert a database row into PredictionRecord."""

        evaluated_at = row["evaluated_at"]

        if evaluated_at:
            evaluated_at = datetime.fromisoformat(
                evaluated_at
            )

        return PredictionRecord(
            database_id=int(row["id"]),
            symbol=row["symbol"],
            action=row["action"],
            confidence=float(row["confidence"]),
            evidence=float(row["evidence"]),
            price_usd=float(row["price_usd"]),
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            analysts=json.loads(
                row["analysts"]
            ),
            reason=row["reason"],
            features=json.loads(
                row["features"]
                or "{}"
            ),
            analysis_snapshot_id=(
                int(row["analysis_snapshot_id"])
                if row["analysis_snapshot_id"] is not None
                else None
            ),
            evaluated=bool(row["evaluated"]),
            correct=(
                bool(row["correct"])
                if row["correct"] is not None
                else None
            ),
            evaluated_price_usd=(
                float(row["evaluated_price_usd"])
                if row["evaluated_price_usd"] is not None
                else None
            ),
            price_change_percent=(
                float(row["price_change_percent"])
                if row["price_change_percent"] is not None
                else None
            ),
            evaluated_at=evaluated_at,
        )
