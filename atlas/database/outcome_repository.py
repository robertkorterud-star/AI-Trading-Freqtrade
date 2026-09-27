"""
ATLAS Outcome Repository

Database access for prediction outcomes.
"""

from datetime import datetime

from atlas.database.connection import Database
from atlas.trading.outcome_tracker import OutcomeRecord


class OutcomeRepository:
    """Stores and retrieves prediction outcomes."""

    def __init__(self, database: Database):
        self.database = database

    def save(
        self,
        prediction_id: int,
        outcome: OutcomeRecord,
        connection=None,
    ):
        """Insert a new prediction outcome."""

        if connection is not None:
            return self._save(
                connection,
                prediction_id,
                outcome,
            )

        with self.database.connect() as owned_connection:
            outcome_id = self._save(
                owned_connection,
                prediction_id,
                outcome,
            )
            owned_connection.commit()

            return outcome_id

    @staticmethod
    def _save(connection, prediction_id: int, outcome: OutcomeRecord):
        """Execute an outcome insert using one SQLite connection."""

        cursor = connection.execute(
            """
            INSERT INTO outcomes (
                prediction_id,
                symbol,
                action,
                prediction_price_usd,
                outcome_price_usd,
                change_percent,
                correct,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prediction_id,
                outcome.symbol,
                outcome.action,
                outcome.prediction_price_usd,
                outcome.outcome_price_usd,
                outcome.change_percent,
                int(outcome.correct),
                outcome.timestamp.isoformat(),
            ),
        )

        return cursor.lastrowid

    def get_all(self):
        """Return all outcomes, newest first."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM outcomes
                ORDER BY timestamp DESC, id DESC
                """
            ).fetchall()

        return [
            self._row_to_outcome(row)
            for row in rows
        ]

    def get_for_prediction(
        self,
        prediction_id: int,
    ):
        """Return outcomes belonging to one prediction."""

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM outcomes
                WHERE prediction_id = ?
                ORDER BY id DESC
                """,
                (prediction_id,),
            ).fetchall()

        return [
            self._row_to_outcome(row)
            for row in rows
        ]

    def count(self):
        """Return number of stored outcomes."""

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM outcomes
                """
            ).fetchone()

        return int(row["count"])

    def correct_count(self):
        """Return number of correct outcomes."""

        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM outcomes
                WHERE correct = 1
                """
            ).fetchone()

        return int(row["count"])

    def clear(self):
        """Delete all stored outcomes."""

        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM outcomes"
            )

            connection.commit()

    @staticmethod
    def _row_to_outcome(row):
        """Convert database row to OutcomeRecord."""

        return OutcomeRecord(
            symbol=row["symbol"],
            action=row["action"],
            prediction_price_usd=float(
                row["prediction_price_usd"]
            ),
            outcome_price_usd=float(
                row["outcome_price_usd"]
            ),
            change_percent=float(
                row["change_percent"]
            ),
            correct=bool(row["correct"]),
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
        )
